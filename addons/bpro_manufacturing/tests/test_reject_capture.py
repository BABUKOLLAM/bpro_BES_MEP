from odoo.exceptions import UserError

from .common import MfgTestCommon


class TestUnifiedRejectCapture(MfgTestCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.reason = cls.env["stock.scrap.reason.tag"].create({"name": "Dimension out of tolerance"})

    def test_recording_completed_qty_only(self):
        mo = self._mo()
        mo.action_confirm()
        wo = mo.workorder_ids
        wo.action_bpro_record_production(qty_completed=5.0)
        self.assertEqual(wo.qty_producing, 5.0)
        self.assertEqual(wo.bpro_qty_rejected, 0.0)

    def test_rejected_qty_without_reason_is_blocked(self):
        mo = self._mo()
        mo.action_confirm()
        wo = mo.workorder_ids
        with self.assertRaises(UserError):
            wo.action_bpro_record_production(qty_completed=9.0, qty_rejected=1.0)

    def test_rejected_qty_with_reason_creates_scrap_and_updates_cumulative(self):
        mo = self._mo()
        mo.action_confirm()
        wo = mo.workorder_ids
        wo.action_bpro_record_production(
            qty_completed=9.0, qty_rejected=1.0, reason_id=self.reason.id
        )
        self.assertEqual(wo.qty_producing, 9.0)
        self.assertEqual(wo.bpro_qty_rejected, 1.0)
        self.assertEqual(wo.bpro_reject_reason_id, self.reason)
        scrap = self.env["stock.scrap"].search([("workorder_id", "=", wo.id)])
        self.assertEqual(len(scrap), 1)
        self.assertEqual(scrap.state, "done")
        self.assertIn(self.reason, scrap.scrap_reason_tag_ids)

    def test_second_reject_accumulates(self):
        mo = self._mo(qty=20.0)
        mo.action_confirm()
        wo = mo.workorder_ids
        wo.action_bpro_record_production(
            qty_completed=15.0, qty_rejected=2.0, reason_id=self.reason.id
        )
        wo.action_bpro_record_production(qty_rejected=3.0, reason_id=self.reason.id)
        self.assertEqual(wo.bpro_qty_rejected, 5.0)

    def test_ui_button_reads_input_fields_and_clears_qty_after(self):
        mo = self._mo(qty=20.0)
        mo.action_confirm()
        wo = mo.workorder_ids
        wo.write({"bpro_reject_qty_input": 4.0, "bpro_reject_reason_id": self.reason.id})
        wo.action_bpro_record_reject_button()
        self.assertEqual(wo.bpro_qty_rejected, 4.0)
        self.assertEqual(
            wo.bpro_reject_qty_input,
            0.0,
            "the input must clear after recording, ready for the next reject event",
        )

    def test_ui_button_is_a_noop_with_no_quantity_entered(self):
        mo = self._mo()
        mo.action_confirm()
        wo = mo.workorder_ids
        wo.action_bpro_record_reject_button()
        self.assertEqual(wo.bpro_qty_rejected, 0.0)
