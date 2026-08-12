from datetime import date, timedelta

from odoo.exceptions import UserError

from .common import RecruitmentTestCommon


class TestJoiningReport(RecruitmentTestCommon):
    """R4.5: the SLA deadline is fixed at creation from the company's
    joining_report_sla policy (2/7/15/30 days) and does NOT retroactively
    shift if that policy changes later."""

    def setUp(self):
        super().setUp()
        self.report_employee = self.env["hr.employee"].create({
            "name": "Joining Report Test Employee", "company_id": self.company.id,
        })

    def _make_report(self, expected_joining_date, **kwargs):
        vals = {
            "employee_id": self.report_employee.id,
            "expected_joining_date": expected_joining_date,
        }
        vals.update(kwargs)
        return self.env["bpro.joining.report"].create(vals)

    def test_sla_deadline_uses_the_companys_policy(self):
        self.company.joining_report_sla = "7"
        report = self._make_report(date(2026, 9, 1))
        self.assertEqual(report.sla_deadline, date(2026, 9, 8))

    def test_sla_deadline_is_not_retroactive_to_a_later_policy_change(self):
        self.company.joining_report_sla = "7"
        report = self._make_report(date(2026, 9, 1))
        self.assertEqual(report.sla_deadline, date(2026, 9, 8))
        self.company.joining_report_sla = "2"
        self.assertEqual(report.sla_deadline, date(2026, 9, 8))

    def test_is_overdue_true_when_pending_past_deadline(self):
        self.company.joining_report_sla = "7"
        report = self._make_report(date.today() - timedelta(days=30))
        self.assertEqual(report.state, "pending")
        self.assertTrue(report.is_overdue)

    def test_is_overdue_false_when_not_yet_past_deadline(self):
        self.company.joining_report_sla = "7"
        report = self._make_report(date.today() + timedelta(days=30))
        self.assertFalse(report.is_overdue)

    def test_is_overdue_false_once_submitted_even_past_deadline(self):
        self.company.joining_report_sla = "7"
        report = self._make_report(date.today() - timedelta(days=30))
        report.actual_joining_date = date.today()
        report.action_submit()
        self.assertFalse(report.is_overdue)

    def test_submit_requires_an_actual_joining_date(self):
        report = self._make_report(date.today())
        with self.assertRaises(UserError):
            report.action_submit()

    def test_submit_sets_state_and_submitted_date(self):
        report = self._make_report(date.today())
        report.actual_joining_date = date.today()
        report.action_submit()
        self.assertEqual(report.state, "submitted")
        self.assertTrue(report.submitted_date)

    def test_submit_twice_raises(self):
        report = self._make_report(date.today())
        report.actual_joining_date = date.today()
        report.action_submit()
        with self.assertRaises(UserError):
            report.action_submit()
