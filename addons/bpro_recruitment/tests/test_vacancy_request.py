from odoo.exceptions import UserError

from .common import RecruitmentTestCommon


class TestVacancyRequest(RecruitmentTestCommon):
    """R4.1: draft -> submitted -> approved/rejected, and the auto-created
    hr.job on approval that the public application page (website_hr_
    recruitment) will publish from."""

    def test_submit_requires_draft_state(self):
        request = self._make_vacancy_request()
        request.action_submit()
        with self.assertRaises(UserError):
            request.action_submit()

    def test_submit_requires_at_least_one_position(self):
        request = self._make_vacancy_request(positions_count=0)
        with self.assertRaises(UserError):
            request.action_submit()

    def test_approve_requires_submitted_state(self):
        request = self._make_vacancy_request()
        with self.assertRaises(UserError):
            request.action_approve()

    def test_approve_creates_a_linked_job_and_stamps_the_approver(self):
        request = self._make_vacancy_request(
            job_title="Senior Process Engineer", positions_count=2,
        )
        request.action_submit()
        request.action_approve()
        self.assertEqual(request.state, "approved")
        self.assertTrue(request.job_id)
        self.assertEqual(request.job_id.name, "Senior Process Engineer")
        self.assertEqual(request.job_id.department_id, request.department_id)
        self.assertEqual(request.job_id.no_of_recruitment, 2)
        self.assertEqual(request.approved_by, self.env.user)
        self.assertTrue(request.approved_date)

    def test_reject_requires_submitted_state(self):
        request = self._make_vacancy_request()
        with self.assertRaises(UserError):
            request.action_reject()

    def test_reject_does_not_create_a_job(self):
        request = self._make_vacancy_request()
        request.action_submit()
        request.action_reject()
        self.assertEqual(request.state, "rejected")
        self.assertFalse(request.job_id)

    def test_reject_wizard_sets_state_and_reason(self):
        request = self._make_vacancy_request()
        request.action_submit()
        wizard = self.env["bpro.vacancy.request.reject.wizard"].create({
            "request_id": request.id,
            "reason": "Headcount frozen this quarter.",
        })
        wizard.action_confirm_reject()
        self.assertEqual(request.state, "rejected")
        self.assertEqual(request.rejection_reason, "Headcount frozen this quarter.")

    def test_reset_draft_requires_rejected_state(self):
        request = self._make_vacancy_request()
        with self.assertRaises(UserError):
            request.action_reset_draft()

    def test_reset_draft_clears_the_rejection_reason(self):
        request = self._make_vacancy_request()
        request.action_submit()
        request.action_reject()
        request.rejection_reason = "Not needed anymore."
        request.action_reset_draft()
        self.assertEqual(request.state, "draft")
        self.assertFalse(request.rejection_reason)

    def test_default_department_is_the_requesting_users_own(self):
        request = self.env["bpro.vacancy.request"].with_user(self.hod_user).create({
            "job_title": "Test Position",
            "positions_count": 1,
            "justification": "Backfill.",
        })
        self.assertEqual(request.department_id, self.department)
