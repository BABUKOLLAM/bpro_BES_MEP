from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestQualityManufacturing(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.company.id)], limit=1
        )
        cls.workcenter = cls.env["mrp.workcenter"].create(
            {
                "name": "Quality Test Work Center",
                "resource_calendar_id": cls.company.resource_calendar_id.id,
                "default_capacity": 1,
            }
        )
        cls.component = cls.env["product.product"].create(
            {"name": "Quality Test Raw Material", "is_storable": True}
        )
        cls.finished = cls.env["product.product"].create(
            {"name": "Quality Test Finished Good", "is_storable": True}
        )
        cls.bom = cls.env["mrp.bom"].create(
            {
                "product_tmpl_id": cls.finished.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [
                    (0, 0, {"product_id": cls.component.id, "product_qty": 2.0}),
                ],
                "operation_ids": [
                    (0, 0, {"name": "Assemble", "workcenter_id": cls.workcenter.id}),
                ],
            }
        )
        cls.env["stock.quant"]._update_available_quantity(
            cls.component, cls.warehouse.lot_stock_id, 1000.0
        )

    def _mo(self, qty=1.0):
        return self.env["mrp.production"].create(
            {
                "product_id": self.finished.id,
                "product_qty": qty,
                "bom_id": self.bom.id,
                "product_uom_id": self.finished.uom_id.id,
            }
        )

    def _confirmed_wo(self):
        mo = self._mo()
        mo.action_confirm()
        return mo.workorder_ids

    def test_no_quality_point_means_no_gate(self):
        wo = self._confirmed_wo()
        wo.qty_producing = 1.0
        wo.button_finish()
        self.assertEqual(wo.state, "done")
        self.assertFalse(wo.bpro_quality_check_ids)

    def test_matching_quality_point_creates_a_pending_check_and_blocks_finish(self):
        self.env["bpro.quality.point"].create(
            {
                "name": "Visual Inspection",
                "operation": "manufacturing",
                "product_tmpl_id": self.finished.product_tmpl_id.id,
            }
        )
        wo = self._confirmed_wo()
        wo.qty_producing = 1.0
        with self.assertRaises(UserError):
            wo.button_finish()
        self.assertEqual(len(wo.bpro_quality_check_ids), 1)
        self.assertEqual(wo.bpro_quality_check_ids.result, "none")

    def test_passing_the_check_unblocks_finish(self):
        self.env["bpro.quality.point"].create(
            {
                "name": "Visual Inspection",
                "operation": "manufacturing",
                "product_tmpl_id": self.finished.product_tmpl_id.id,
            }
        )
        wo = self._confirmed_wo()
        wo.qty_producing = 1.0
        with self.assertRaises(UserError):
            wo.button_finish()
        wo.bpro_quality_check_ids.action_bpro_pass()
        wo.button_finish()
        self.assertEqual(wo.state, "done")

    def test_failed_check_still_blocks_finish(self):
        self.env["bpro.quality.point"].create(
            {
                "name": "Visual Inspection",
                "operation": "manufacturing",
                "product_tmpl_id": self.finished.product_tmpl_id.id,
            }
        )
        wo = self._confirmed_wo()
        wo.qty_producing = 1.0
        with self.assertRaises(UserError):
            wo.button_finish()
        wo.bpro_quality_check_ids.action_bpro_fail()
        with self.assertRaises(UserError):
            wo.button_finish()

    def test_point_for_a_different_operation_does_not_apply(self):
        self.env["bpro.quality.point"].create(
            {
                "name": "Incoming Only Check",
                "operation": "incoming",
                "product_tmpl_id": self.finished.product_tmpl_id.id,
            }
        )
        wo = self._confirmed_wo()
        wo.qty_producing = 1.0
        wo.button_finish()
        self.assertEqual(wo.state, "done")
        self.assertFalse(wo.bpro_quality_check_ids)
