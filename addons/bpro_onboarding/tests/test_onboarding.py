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

    def test_new_client_site_has_no_starter_kit_content(self):
        """A freshly onboarded client must go straight to login, not
        Odoo's generic 'Your Company' starter marketing site."""
        self._wizard().action_onboard()
        website = self.env["website"].search(
            [("name", "=", "Onboard Test Client Portal")]
        )
        self.assertEqual(website.homepage_url, "/web/login")
        stray_pages = self.env["website.page"].search(
            [
                ("website_id", "=", website.id),
                ("url", "!=", "/"),
                ("is_published", "=", True),
            ]
        )
        self.assertFalse(stray_pages, "no published starter-kit pages should remain")
        stray_menus = self.env["website.menu"].search(
            [
                ("website_id", "=", website.id),
                ("url", "not in", ["/", "/slides", "/default-main-menu"]),
            ]
        )
        self.assertFalse(stray_menus, "no starter-kit menu items should remain")

    def test_scrub_removes_fake_contact_details(self):
        """Odoo's website starter kit bakes literal placeholder contact
        info ("+1 555-555-5556" etc) into per-site header/footer views.
        The scrub must strip the whole wrapping block, not just hide it."""
        self._wizard().action_onboard()
        website = self.env["website"].search(
            [("name", "=", "Onboard Test Client Portal")]
        )
        view = self.env["ir.ui.view"].create(
            {
                "name": "Fake footer for test",
                "type": "qweb",
                "website_id": website.id,
                "arch": (
                    '<div><p class="mb-1">123 Fake St</p>'
                    '<ul><li><a href="tel:+1 555-555-5556">'
                    "+1 555-555-5556</a></li></ul></div>"
                ),
            }
        )
        website._bpro_scrub_fake_contact_details()
        self.assertNotIn("555-555-5556", view.arch_db)

    def test_duplicate_company_rejected(self):
        self._wizard().action_onboard()
        with self.assertRaises(UserError):
            self._wizard(hr_email="other@test.example").action_onboard()

    def test_duplicate_login_rejected(self):
        self._wizard().action_onboard()
        with self.assertRaises(UserError):
            self._wizard(client_name="Different Client").action_onboard()
