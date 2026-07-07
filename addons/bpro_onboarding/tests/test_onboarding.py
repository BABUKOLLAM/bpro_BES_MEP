from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestOnboarding(TransactionCase):
    def _wizard(self, **overrides):
        vals = {
            "client_name": "Onboard Test Client",
            "hr_name": "Onboard HR",
            "hr_email": "onboard-hr@test.example",
            "hr_password": "test-password-123",
            "first_department": "Test Ops",
            "portal_domain": "onboard.test.example",
        }
        vals.update(overrides)
        return self.env["bpro.client.onboarding"].create(vals)

    def test_onboarding_creates_full_stack(self):
        self._wizard().action_onboard()
        company = self.env["res.company"].search(
            [("name", "=", "Onboard Test Client")]
        )
        self.assertTrue(company)
        self.assertTrue(company.parent_id, "client must sit under the master company")
        user = self.env["res.users"].search(
            [("login", "=", "onboard-hr@test.example")]
        )
        self.assertEqual(user.company_id, company)
        self.assertIn(self.env.ref("bpro_base.group_client_hr"), user.groups_id)
        employee = self.env["hr.employee"].search(
            [("user_id", "=", user.id)]
        )
        self.assertEqual(employee.company_id, company)
        self.assertEqual(employee.department_id.name, "Test Ops")
        website = self.env["website"].search(
            [("name", "=", "Onboard Test Client Portal")]
        )
        self.assertEqual(website.company_id, company)

    def test_duplicate_company_rejected(self):
        self._wizard().action_onboard()
        with self.assertRaises(UserError):
            self._wizard(hr_email="other@test.example").action_onboard()

    def test_duplicate_login_rejected(self):
        self._wizard().action_onboard()
        with self.assertRaises(UserError):
            self._wizard(client_name="Different Client").action_onboard()
