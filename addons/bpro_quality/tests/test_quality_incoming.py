from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestQualityIncoming(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env["res.partner"].create({"name": "Quality Test Vendor"})
        cls.product = cls.env["product.product"].create(
            {"name": "Quality Test Component", "is_storable": True}
        )

    def _received_picking(self):
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
        picking = po.picking_ids
        picking.move_ids.quantity = 5.0
        picking.move_ids.picked = True
        return picking

    def test_no_quality_point_means_no_gate(self):
        picking = self._received_picking()
        picking.button_validate()
        self.assertEqual(picking.state, "done")
        self.assertFalse(picking.bpro_quality_check_ids)

    def test_matching_quality_point_creates_a_pending_check_and_blocks_validation(self):
        self.env["bpro.quality.point"].create(
            {
                "name": "Incoming Visual Check",
                "operation": "incoming",
                "product_tmpl_id": self.product.product_tmpl_id.id,
            }
        )
        picking = self._received_picking()
        with self.assertRaises(UserError):
            picking.button_validate()
        self.assertEqual(len(picking.bpro_quality_check_ids), 1)
        self.assertEqual(picking.bpro_quality_check_ids.result, "none")

    def test_passing_the_check_unblocks_validation(self):
        self.env["bpro.quality.point"].create(
            {
                "name": "Incoming Visual Check",
                "operation": "incoming",
                "product_tmpl_id": self.product.product_tmpl_id.id,
            }
        )
        picking = self._received_picking()
        with self.assertRaises(UserError):
            picking.button_validate()
        picking.bpro_quality_check_ids.action_bpro_pass()
        picking.button_validate()
        self.assertEqual(picking.state, "done")

    def test_category_level_point_applies_to_any_matching_product(self):
        self.env["bpro.quality.point"].create(
            {
                "name": "Category Check",
                "operation": "incoming",
                "product_category_id": self.product.categ_id.id,
            }
        )
        picking = self._received_picking()
        with self.assertRaises(UserError):
            picking.button_validate()
        self.assertEqual(len(picking.bpro_quality_check_ids), 1)

    def test_point_for_a_different_operation_does_not_apply(self):
        self.env["bpro.quality.point"].create(
            {
                "name": "Manufacturing Only Check",
                "operation": "manufacturing",
                "product_tmpl_id": self.product.product_tmpl_id.id,
            }
        )
        picking = self._received_picking()
        picking.button_validate()
        self.assertEqual(picking.state, "done")
        self.assertFalse(picking.bpro_quality_check_ids)
