from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestVendorPerformance(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env["res.partner"].create({"name": "Logistics Test Vendor"})
        cls.product = cls.env["product.product"].create(
            {"name": "Logistics Test Component", "is_storable": True}
        )

    def _po(self, promised_delta_days):
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_qty": 5.0,
                            "price_unit": 10.0,
                        },
                    )
                ],
            }
        )
        po.button_confirm()
        po.order_line.date_planned = fields.Datetime.now() + timedelta(
            days=promised_delta_days
        )
        return po

    def _validate(self, po):
        picking = po.picking_ids
        picking.move_ids.quantity = picking.move_ids.product_uom_qty
        picking.move_ids.picked = True
        picking.button_validate()
        return picking

    def test_receiving_before_the_promised_date_is_on_time(self):
        po = self._po(promised_delta_days=5)
        picking = self._validate(po)
        self.assertTrue(picking.bpro_on_time)
        self.assertLess(picking.bpro_delay_days, 0)

    def test_receiving_after_the_promised_date_is_late(self):
        po = self._po(promised_delta_days=-5)
        picking = self._validate(po)
        self.assertFalse(picking.bpro_on_time)
        self.assertGreater(picking.bpro_delay_days, 0)

    def test_picking_not_linked_to_a_purchase_order_is_unaffected(self):
        source = self.env["stock.location"].create(
            {"name": "Logistics Test Source", "usage": "internal"}
        )
        destination = self.env["stock.location"].create(
            {"name": "Logistics Test Destination", "usage": "internal"}
        )
        picking_type = self.env["stock.warehouse"].search([], limit=1).int_type_id
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": source.id,
                "location_dest_id": destination.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "name": self.product.name,
                            "product_id": self.product.id,
                            "product_uom_qty": 1.0,
                            "product_uom": self.product.uom_id.id,
                            "location_id": source.id,
                            "location_dest_id": destination.id,
                        },
                    )
                ],
            }
        )
        picking.action_confirm()
        picking.move_ids.quantity = 1.0
        picking.move_ids.picked = True
        picking.button_validate()
        self.assertFalse(picking.purchase_id)
        self.assertFalse(picking.bpro_on_time)
        self.assertFalse(picking.bpro_promised_date)

    def test_not_yet_done_picking_has_no_computed_performance(self):
        po = self._po(promised_delta_days=5)
        picking = po.picking_ids
        self.assertNotEqual(picking.state, "done")
        self.assertFalse(picking.bpro_promised_date)
        self.assertEqual(picking.bpro_delay_days, 0.0)
