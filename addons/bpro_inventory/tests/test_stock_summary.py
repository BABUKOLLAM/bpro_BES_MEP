from odoo.tests.common import TransactionCase


class TestStockSummary(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.location_a = cls.env["stock.location"].create(
            {"name": "Test Godown A", "usage": "internal", "company_id": cls.company.id}
        )
        cls.location_b = cls.env["stock.location"].create(
            {"name": "Test Godown B", "usage": "internal", "company_id": cls.company.id}
        )
        cls.product_1 = cls.env["product.product"].create(
            {"name": "Summary Widget 1", "is_storable": True, "standard_price": 12.5}
        )
        cls.product_2 = cls.env["product.product"].create(
            {"name": "Summary Widget 2", "is_storable": True, "standard_price": 4.0}
        )
        # widget 1 sits in both godowns; widget 2 only in A
        cls.env["stock.quant"]._update_available_quantity(cls.product_1, cls.location_a, 100.0)
        cls.env["stock.quant"]._update_available_quantity(cls.product_1, cls.location_b, 30.0)
        cls.env["stock.quant"]._update_available_quantity(cls.product_2, cls.location_a, 50.0)

    def test_summary_lists_one_row_per_product_per_location(self):
        wizard = self.env["bpro.stock.summary.wizard"].create({})
        data = wizard._get_stock_summary_data(self.company)
        rows = {
            (l["product_id"], l["location_id"]): l for l in data["lines"]
        }
        self.assertEqual(
            rows[(self.product_1.id, self.location_a.id)]["quantity"], 100.0
        )
        self.assertEqual(
            rows[(self.product_1.id, self.location_b.id)]["quantity"], 30.0
        )
        self.assertEqual(
            rows[(self.product_2.id, self.location_a.id)]["quantity"], 50.0
        )

    def test_summary_value_is_qty_times_standard_price(self):
        wizard = self.env["bpro.stock.summary.wizard"].create({})
        data = wizard._get_stock_summary_data(self.company)
        rows = {
            (l["product_id"], l["location_id"]): l for l in data["lines"]
        }
        # hand-computed: 100 * 12.5 = 1250.0
        self.assertEqual(
            rows[(self.product_1.id, self.location_a.id)]["value"], 1250.0
        )
        # hand-computed: 50 * 4.0 = 200.0
        self.assertEqual(
            rows[(self.product_2.id, self.location_a.id)]["value"], 200.0
        )

    def test_summary_total_value_is_sum_of_lines(self):
        wizard = self.env["bpro.stock.summary.wizard"].create({})
        data = wizard._get_stock_summary_data(self.company)
        # hand-computed: (100*12.5) + (30*12.5) + (50*4.0) = 1250 + 375 + 200 = 1825.0
        self.assertEqual(data["total_value"], 1825.0)

    def test_zero_quantity_quants_are_excluded(self):
        zero_product = self.env["product.product"].create(
            {"name": "Zero Stock Widget", "is_storable": True, "standard_price": 9.0}
        )
        self.env["stock.quant"]._update_available_quantity(
            zero_product, self.location_a, 5.0
        )
        self.env["stock.quant"]._update_available_quantity(
            zero_product, self.location_a, -5.0
        )
        wizard = self.env["bpro.stock.summary.wizard"].create({})
        data = wizard._get_stock_summary_data(self.company)
        product_ids = {l["product_id"] for l in data["lines"]}
        self.assertNotIn(zero_product.id, product_ids)

    def test_action_generate_populates_line_ids(self):
        wizard = self.env["bpro.stock.summary.wizard"].create({})
        wizard.action_generate()
        self.assertTrue(len(wizard.line_ids) >= 3)
        self.assertEqual(wizard.total_value, sum(wizard.line_ids.mapped("value")))
