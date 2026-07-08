from odoo.exceptions import UserError

from .common import HrTestCommon


class TestExpenseApproval(HrTestCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["bpro.policy"].create(
            {
                "company_id": cls.company.id,
                "key": "hr_expense_finance_approval_pct",
                "numeric_value": 500.0,
            }
        )

    def test_small_expense_confirms_without_finance_approval(self):
        sheet = self._sheet(100.0)
        sheet.action_submit_sheet()
        self.assertEqual(sheet.bpro_finance_approval_state, "none")
        sheet.action_approve_expense_sheets()
        self.assertEqual(sheet.state, "approve")

    def test_large_expense_blocks_manager_approval(self):
        sheet = self._sheet(1000.0)
        sheet.action_submit_sheet()
        self.assertEqual(sheet.bpro_finance_approval_state, "pending")
        with self.assertRaises(UserError):
            sheet.action_approve_expense_sheets()
        self.assertEqual(sheet.state, "submit")

    def test_finance_approval_unblocks_manager_approval(self):
        sheet = self._sheet(1000.0)
        sheet.action_submit_sheet()
        sheet.action_bpro_finance_approve()
        sheet.action_approve_expense_sheets()
        self.assertEqual(sheet.state, "approve")

    def test_finance_rejection_blocks_manager_approval(self):
        sheet = self._sheet(1000.0)
        sheet.action_submit_sheet()
        sheet.action_bpro_finance_reject()
        with self.assertRaises(UserError):
            sheet.action_approve_expense_sheets()

    def test_no_threshold_configured_defaults_to_always_requiring_approval(self):
        # bpro.policy.get_value's own default is 0.0 (fail closed, same
        # convention as the sales-discount and 3-way-match thresholds
        # elsewhere in this codebase) - remove the policy set up above to
        # exercise that fallback.
        self.env["bpro.policy"].search(
            [
                ("company_id", "=", self.company.id),
                ("key", "=", "hr_expense_finance_approval_pct"),
            ]
        ).unlink()
        sheet = self._sheet(1.0)
        sheet.action_submit_sheet()
        self.assertEqual(sheet.bpro_finance_approval_state, "pending")
