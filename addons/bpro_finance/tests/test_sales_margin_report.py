from datetime import date

from odoo.tests.common import TransactionCase


class TestSalesMarginReport(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.partner = cls.env["res.partner"].create({"name": "Margin Test Customer"})
        cls.product_a = cls.env["product.product"].create(
            {"name": "Margin Widget A", "list_price": 100.0, "standard_price": 60.0}
        )
        cls.product_b = cls.env["product.product"].create(
            {"name": "Margin Widget B", "list_price": 50.0, "standard_price": 55.0}
        )

    def _confirmed_order(self, order_date, lines):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "date_order": order_date,
                "order_line": [
                    (0, 0, {"product_id": p.id, "product_uom_qty": qty, "price_unit": price})
                    for p, qty, price in lines
                ],
            }
        )
        order.action_confirm()
        # action_confirm() deliberately overwrites date_order to "now" (the
        # actual confirmation time) - real, documented Odoo behavior, not a
        # bug. Restore the requested test date afterward so these fixtures
        # land in the period being tested.
        order.write({"date_order": order_date})
        return order

    def test_revenue_cost_and_margin_hand_computed(self):
        # product_a: 3 units @ 100 = 300 revenue; cost = 3 x 60 = 180; margin = 120
        self._confirmed_order(
            "2026-04-10 10:00:00", [(self.product_a, 3, 100.0)]
        )
        wizard = self.env["bpro.sales.margin.wizard"].create(
            {"date_from": date(2026, 4, 1), "date_to": date(2026, 4, 30)}
        )
        data = wizard._get_sales_margin_data(self.company, date(2026, 4, 1), date(2026, 4, 30))
        line = next(l for l in data["lines"] if l["product_id"] == self.product_a.id)
        self.assertEqual(line["qty_sold"], 3.0)
        self.assertEqual(line["revenue"], 300.0)
        self.assertEqual(line["cost"], 180.0)
        self.assertEqual(line["margin"], 120.0)
        self.assertAlmostEqual(line["margin_pct"], 120.0 / 300.0)

    def test_negative_margin_when_cost_exceeds_price(self):
        # product_b: 2 units @ 50 = 100 revenue; cost = 2 x 55 = 110; margin = -10
        self._confirmed_order(
            "2026-04-12 10:00:00", [(self.product_b, 2, 50.0)]
        )
        data = self.env["bpro.sales.margin.wizard"]._get_sales_margin_data(
            self.company, date(2026, 4, 1), date(2026, 4, 30)
        )
        line = next(l for l in data["lines"] if l["product_id"] == self.product_b.id)
        self.assertEqual(line["margin"], -10.0)

    def test_multiple_orders_for_same_product_are_aggregated(self):
        self._confirmed_order("2026-04-05 10:00:00", [(self.product_a, 2, 100.0)])
        self._confirmed_order("2026-04-20 10:00:00", [(self.product_a, 5, 100.0)])
        data = self.env["bpro.sales.margin.wizard"]._get_sales_margin_data(
            self.company, date(2026, 4, 1), date(2026, 4, 30)
        )
        line = next(l for l in data["lines"] if l["product_id"] == self.product_a.id)
        # hand-computed: (2+5) units, revenue 700, cost 7*60=420, margin 280
        self.assertEqual(line["qty_sold"], 7.0)
        self.assertEqual(line["revenue"], 700.0)
        self.assertEqual(line["cost"], 420.0)
        self.assertEqual(line["margin"], 280.0)

    def test_orders_outside_date_range_are_excluded(self):
        self._confirmed_order("2026-03-31 10:00:00", [(self.product_a, 9, 100.0)])
        data = self.env["bpro.sales.margin.wizard"]._get_sales_margin_data(
            self.company, date(2026, 4, 1), date(2026, 4, 30)
        )
        product_ids = {l["product_id"] for l in data["lines"]}
        self.assertNotIn(self.product_a.id, product_ids)

    def test_unconfirmed_quotations_are_excluded(self):
        self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "date_order": "2026-04-15 10:00:00",
                "order_line": [
                    (0, 0, {"product_id": self.product_a.id, "product_uom_qty": 4, "price_unit": 100.0})
                ],
            }
        )
        data = self.env["bpro.sales.margin.wizard"]._get_sales_margin_data(
            self.company, date(2026, 4, 1), date(2026, 4, 30)
        )
        product_ids = {l["product_id"] for l in data["lines"]}
        self.assertNotIn(self.product_a.id, product_ids)

    def test_action_generate_populates_totals(self):
        self._confirmed_order("2026-04-10 10:00:00", [(self.product_a, 3, 100.0)])
        wizard = self.env["bpro.sales.margin.wizard"].create(
            {"date_from": date(2026, 4, 1), "date_to": date(2026, 4, 30)}
        )
        wizard.action_generate()
        self.assertEqual(wizard.total_revenue, 300.0)
        self.assertEqual(wizard.total_cost, 180.0)
        self.assertEqual(wizard.total_margin, 120.0)
