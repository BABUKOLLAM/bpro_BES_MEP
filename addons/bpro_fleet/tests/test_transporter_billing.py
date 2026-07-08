from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestTransporterBilling(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.env["account.chart.template"].try_loading(
            "generic_coa", cls.company, install_demo=False
        )
        cls.expense_account = cls.env["account.account"].search(
            [("account_type", "=", "expense")], limit=1
        )
        cls.brand = cls.env["fleet.vehicle.model.brand"].create({"name": "Test Brand"})
        cls.model = cls.env["fleet.vehicle.model"].create(
            {"name": "Test Model", "brand_id": cls.brand.id}
        )
        cls.transporter = cls.env["res.partner"].create({"name": "Test Transporter"})
        cls.hired_vehicle = cls.env["fleet.vehicle"].create(
            {
                "model_id": cls.model.id,
                "bpro_ownership_type": "hired",
                "bpro_transporter_id": cls.transporter.id,
                "bpro_trip_expense_account_id": cls.expense_account.id,
                "bpro_trip_rate": 2000.0,
            }
        )
        cls.owned_vehicle = cls.env["fleet.vehicle"].create(
            {"model_id": cls.model.id, "bpro_ownership_type": "owned"}
        )
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.company.id)], limit=1
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Fleet Test Product", "is_storable": True}
        )
        cls.env["stock.quant"]._update_available_quantity(
            cls.product, cls.warehouse.lot_stock_id, 10.0
        )

    def _done_batch(self, vehicle):
        batch = self.env["stock.picking.batch"].create({"vehicle_id": vehicle.id})
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.warehouse.out_type_id.id,
                "location_id": self.warehouse.lot_stock_id.id,
                "location_dest_id": self.env.ref(
                    "stock.stock_location_customers"
                ).id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "name": self.product.name,
                            "product_id": self.product.id,
                            "product_uom_qty": 1.0,
                            "product_uom": self.product.uom_id.id,
                            "location_id": self.warehouse.lot_stock_id.id,
                            "location_dest_id": self.env.ref(
                                "stock.stock_location_customers"
                            ).id,
                        },
                    )
                ],
            }
        )
        batch.picking_ids = [(4, picking.id)]
        batch.action_confirm()
        picking.action_assign()
        picking.move_ids.quantity = 1.0
        picking.move_ids.picked = True
        picking.button_validate()
        return batch

    def _draft_batch(self, vehicle):
        return self.env["stock.picking.batch"].create({"vehicle_id": vehicle.id})

    def test_trip_cost_defaults_from_hired_vehicle_rate(self):
        batch = self._draft_batch(self.hired_vehicle)
        self.assertEqual(batch.bpro_trip_cost, 2000.0)

    def test_trip_cost_is_zero_for_owned_vehicle(self):
        batch = self._draft_batch(self.owned_vehicle)
        self.assertEqual(batch.bpro_trip_cost, 0.0)

    def test_completed_hired_batch_can_be_billed(self):
        batch = self._done_batch(self.hired_vehicle)
        self.assertEqual(batch.state, "done")
        batch.action_bpro_create_transporter_bill()
        bill = batch.bpro_transporter_bill_id
        self.assertTrue(bill)
        self.assertEqual(bill.partner_id, self.transporter)
        self.assertEqual(bill.move_type, "in_invoice")
        self.assertEqual(sum(bill.invoice_line_ids.mapped("price_subtotal")), 2000.0)

    def test_owned_vehicle_batch_cannot_be_billed(self):
        batch = self._done_batch(self.owned_vehicle)
        with self.assertRaises(UserError):
            batch.action_bpro_create_transporter_bill()

    def test_undone_batch_cannot_be_billed(self):
        batch = self._draft_batch(self.hired_vehicle)
        with self.assertRaises(UserError):
            batch.action_bpro_create_transporter_bill()

    def test_billing_twice_is_rejected(self):
        batch = self._done_batch(self.hired_vehicle)
        batch.action_bpro_create_transporter_bill()
        with self.assertRaises(UserError):
            batch.action_bpro_create_transporter_bill()
