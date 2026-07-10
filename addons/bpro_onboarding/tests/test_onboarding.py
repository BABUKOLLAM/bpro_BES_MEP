import base64

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase

# smallest valid PNG (1x1 transparent pixel) - Odoo validates logo/image
# fields are real images, so tests can't just use arbitrary bytes
TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42Y"
    "AAAAASUVORK5CYII="
)


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
        for xmlid in (
            "sales_team.group_sale_manager",
            "stock.group_stock_manager",
            "purchase.group_purchase_manager",
            "account.group_account_manager",
            "hr.group_hr_manager",
            "mrp.group_mrp_manager",
            "maintenance.group_equipment_manager",
            "project.group_project_manager",
            "fleet.fleet_group_manager",
        ):
            self.assertIn(
                self.env.ref(xmlid),
                user.groups_id,
                f"onboarded HR admin must get {xmlid} to configure their company's ERP apps",
            )
        employee = self.env["hr.employee"].search(
            [("user_id", "=", user.id)]
        )
        self.assertEqual(employee.company_id, company)
        self.assertEqual(employee.department_id.name, "Test Ops")
        website = self.env["website"].search(
            [("name", "=", "Onboard Test Client Portal")]
        )
        self.assertEqual(website.company_id, company)

    def test_onboarding_sets_address_and_tax_registration(self):
        kerala = self.env["res.country.state"].search(
            [("code", "=", "KL"), ("country_id", "=", self.env.ref("base.in").id)],
            limit=1,
        )
        self._wizard(
            street="1st Floor, Example Complex",
            street2="Example Road",
            city="Ernakulam",
            state_id=kerala.id,
            zip="682001",
            phone="09876543210",
            # real-format GSTIN/PAN required by l10n_in's validation; this is
            # the same constant l10n_in itself uses as a "known valid" test
            # number (see TEST_GST_NUMBER in l10n_in/models/res_partner.py),
            # with its embedded PAN (chars 3-12) as the PAN field.
            vat="36AABCT1332L011",
            l10n_in_pan="AABCT1332L",
        ).action_onboard()
        company = self.env["res.company"].search(
            [("name", "=", "Onboard Test Client")]
        )
        self.assertEqual(company.street, "1st Floor, Example Complex")
        self.assertEqual(company.city, "Ernakulam")
        self.assertEqual(company.state_id, kerala)
        self.assertEqual(company.zip, "682001")
        self.assertEqual(company.country_id, self.env.ref("base.in"))
        self.assertEqual(company.phone, "09876543210")
        self.assertEqual(company.vat, "36AABCT1332L011")
        self.assertEqual(company.l10n_in_pan, "AABCT1332L")

    def test_onboarding_creates_a_default_warehouse(self):
        """Native res.company.create() (stock module) sets up per-company
        locations/sequences but never a stock.warehouse in production -
        without one, Inventory/Manufacturing/Purchase have nowhere to
        receive or store stock for the new company. (Under TransactionCase
        tests specifically, that same native create() already provisions
        one default warehouse per company for test isolation, so this
        checks the guard doesn't duplicate it rather than asserting our
        own code ran - the exact warehouse.code depends on which of the
        two equivalent code paths created it.)"""
        self._wizard().action_onboard()
        company = self.env["res.company"].search(
            [("name", "=", "Onboard Test Client")]
        )
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", company.id)]
        )
        self.assertEqual(len(warehouse), 1)
        self.assertEqual(warehouse.partner_id, company.partner_id)
        self.assertTrue(
            warehouse.lot_stock_id,
            "a real internal stock location must exist for this company",
        )

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

    def test_strip_starter_content_syncs_real_logo(self):
        """website.logo is a field distinct from res.company.logo and
        defaults to Odoo's generic 'Your Logo' placeholder graphic when
        a site is auto-created (e.g. the master site on first install,
        before any of our code ever touches it) - _bpro_strip_starter_
        content must copy the real company logo onto the site."""
        company = self.env["res.company"].create(
            {"name": "Logo Test Co", "logo": base64.b64encode(TINY_PNG).decode()}
        )
        website = self.env["website"].create(
            {"name": "Logo Test Site", "company_id": company.id}
        )
        self.assertNotEqual(website.logo, company.logo, "starts out mismatched")
        website._bpro_strip_starter_content()
        self.assertEqual(website.logo, company.logo)

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
