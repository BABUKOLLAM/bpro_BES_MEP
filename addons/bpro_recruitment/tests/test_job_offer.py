from odoo.exceptions import UserError

from .common import RecruitmentTestCommon


class TestJobOffer(RecruitmentTestCommon):
    """R4.3 (offer send/accept/decline via the portal token) and R4.4
    (hiring finalization: unique employee code, employee record, and the
    auto-created R4.5 joining-report tracker)."""

    def test_send_requires_draft_state(self):
        offer = self._make_offer()
        offer.action_send()
        with self.assertRaises(UserError):
            offer.action_send()

    def test_send_requires_the_applicant_to_have_an_email(self):
        applicant = self._make_applicant(email_from=False)
        offer = self._make_offer(applicant=applicant)
        with self.assertRaises(UserError):
            offer.action_send()

    def test_send_moves_to_sent_and_issues_a_portal_token(self):
        offer = self._make_offer()
        self.assertFalse(offer.access_token)
        offer.action_send()
        self.assertEqual(offer.state, "sent")
        self.assertTrue(offer.access_token)

    def test_accept_from_portal_requires_sent_state(self):
        offer = self._make_offer()
        with self.assertRaises(UserError):
            offer.action_accept_from_portal()

    def test_accept_from_portal_sets_state_and_accepted_date(self):
        offer = self._make_offer()
        offer.action_send()
        offer.action_accept_from_portal()
        self.assertEqual(offer.state, "accepted")
        self.assertTrue(offer.accepted_date)

    def test_decline_from_portal_requires_sent_state(self):
        offer = self._make_offer()
        with self.assertRaises(UserError):
            offer.action_decline_from_portal("Took another offer.")

    def test_decline_from_portal_sets_state_date_and_reason(self):
        offer = self._make_offer()
        offer.action_send()
        offer.action_decline_from_portal("Took another offer.")
        self.assertEqual(offer.state, "declined")
        self.assertTrue(offer.declined_date)
        self.assertEqual(offer.declined_reason, "Took another offer.")

    def test_finalize_hiring_requires_accepted_state(self):
        offer = self._make_offer()
        offer.action_send()
        with self.assertRaises(UserError):
            offer.action_finalize_hiring()

    def test_finalize_hiring_creates_an_employee_with_a_unique_code(self):
        offer = self._make_offer()
        offer.action_send()
        offer.action_accept_from_portal()
        offer.action_finalize_hiring()
        self.assertTrue(offer.employee_id)
        self.assertTrue(offer.employee_id.employee_code)
        self.assertTrue(offer.finalized_date)

    def test_finalize_hiring_twice_raises(self):
        offer = self._make_offer()
        offer.action_send()
        offer.action_accept_from_portal()
        offer.action_finalize_hiring()
        with self.assertRaises(UserError):
            offer.action_finalize_hiring()

    def test_finalize_hiring_auto_creates_a_joining_report(self):
        offer = self._make_offer(joining_date="2026-10-01")
        offer.action_send()
        offer.action_accept_from_portal()
        offer.action_finalize_hiring()
        report = self.env["bpro.joining.report"].search([
            ("offer_id", "=", offer.id)
        ])
        self.assertEqual(len(report), 1)
        self.assertEqual(report.employee_id, offer.employee_id)
        self.assertEqual(str(report.expected_joining_date), "2026-10-01")

    def test_two_finalized_offers_get_distinct_employee_codes(self):
        offer_a = self._make_offer()
        offer_a.action_send()
        offer_a.action_accept_from_portal()
        offer_a.action_finalize_hiring()

        offer_b = self._make_offer()
        offer_b.action_send()
        offer_b.action_accept_from_portal()
        offer_b.action_finalize_hiring()

        self.assertNotEqual(
            offer_a.employee_id.employee_code, offer_b.employee_id.employee_code
        )
