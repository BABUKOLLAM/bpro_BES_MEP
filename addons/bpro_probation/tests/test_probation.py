from datetime import date

from dateutil.relativedelta import relativedelta

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestProbation(TransactionCase):
    """R6.3 - probation starts automatically at hiring finalization,
    never for imported employees, and the confirm/extend decisions
    behave."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.company.probation_months = 6

    def _hire(self, name, joining):
        candidate = self.env["hr.candidate"].create({
            "partner_name": name, "email_from": f"{name.replace(' ', '.')}@example.com",
        })
        job = self.env["hr.job"].create({"name": f"{name} role"})
        applicant = self.env["hr.applicant"].create({
            "candidate_id": candidate.id, "job_id": job.id,
        })
        offer = self.env["bpro.job.offer"].create({
            "applicant_id": applicant.id,
            "proposed_designation": "Test Role",
            "joining_date": joining,
        })
        offer.action_send()
        offer.action_accept_from_portal()
        offer.action_finalize_hiring()
        return offer.employee_id

    def test_finalize_hiring_starts_probation(self):
        employee = self._hire("Probation Hire", date(2026, 9, 1))
        self.assertEqual(employee.probation_state, "probation")
        self.assertEqual(
            employee.probation_end_date,
            date(2026, 9, 1) + relativedelta(months=6),
        )

    def test_imported_employee_stays_confirmed(self):
        employee = self.env["hr.employee"].create({"name": "Imported Employee"})
        self.assertEqual(employee.probation_state, "confirmed")

    def test_confirm_and_extend(self):
        employee = self._hire("Confirm Hire", date(2026, 9, 1))
        original_end = employee.probation_end_date
        employee.action_extend_probation(months=3)
        self.assertEqual(
            employee.probation_end_date, original_end + relativedelta(months=3)
        )
        employee.action_confirm_probation()
        self.assertEqual(employee.probation_state, "confirmed")
        self.assertTrue(employee.confirmation_date)
        with self.assertRaises(UserError):
            employee.action_confirm_probation()
        with self.assertRaises(UserError):
            employee.action_extend_probation()

    def test_cron_posts_due_reminder(self):
        employee = self._hire("Overdue Hire", date(2026, 9, 1))
        employee.probation_end_date = date(2020, 1, 1)
        before = len(employee.message_ids)
        self.env["hr.employee"]._cron_probation_due_reminders()
        self.assertGreater(len(employee.message_ids), before)
        # A confirmed employee never gets a reminder.
        employee.action_confirm_probation()
        count = len(employee.message_ids)
        self.env["hr.employee"]._cron_probation_due_reminders()
        self.assertEqual(len(employee.message_ids), count)
