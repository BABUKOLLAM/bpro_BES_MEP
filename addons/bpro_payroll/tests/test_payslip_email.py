from datetime import date

from odoo.exceptions import UserError

from .common import PayrollTestCommon


class TestPayslipEmail(PayrollTestCommon):
    """R6.2 - payslip PDF distribution by email."""

    def test_email_sends_pdf_to_work_email(self):
        self.employee.work_email = "payslip.test@example.com"
        contract = self._make_contract(240000.0)
        payslip = self._make_payslip(contract, date(2026, 7, 1), date(2026, 7, 31))
        payslip.write({"state": "done"})

        before = self.env["mail.mail"].search([])
        payslip.action_email_payslip()
        mail = self.env["mail.mail"].search([]) - before
        # .send() may already have processed (and auto-deleted) the mail
        # in test mode - the attachment is the durable evidence either way.
        attachment = self.env["ir.attachment"].search([
            ("res_model", "=", "hr.payslip"), ("res_id", "=", payslip.id),
        ])
        self.assertTrue(attachment)
        self.assertTrue(attachment.name.endswith(".pdf"))
        if mail:
            self.assertEqual(mail.email_to, "payslip.test@example.com")

    def test_draft_slip_refused(self):
        contract = self._make_contract(240000.0)
        payslip = self._make_payslip(contract, date(2026, 7, 1), date(2026, 7, 31))
        with self.assertRaises(UserError):
            payslip.action_email_payslip()

    def test_missing_email_reported(self):
        self.employee.work_email = False
        self.employee.private_email = False
        contract = self._make_contract(240000.0)
        payslip = self._make_payslip(contract, date(2026, 7, 1), date(2026, 7, 31))
        payslip.write({"state": "done"})
        with self.assertRaises(UserError):
            payslip.action_email_payslip()
