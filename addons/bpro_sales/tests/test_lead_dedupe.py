from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestLeadDedupe(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")

    def test_duplicate_email_blocked(self):
        self.env["crm.lead"].create(
            {
                "name": "First Lead",
                "email_from": "buyer@acme.example",
                "company_id": self.company.id,
            }
        )
        with self.assertRaises(ValidationError):
            self.env["crm.lead"].create(
                {
                    "name": "Second Lead",
                    "email_from": "buyer@acme.example",
                    "company_id": self.company.id,
                }
            )

    def test_duplicate_phone_blocked(self):
        self.env["crm.lead"].create(
            {
                "name": "First Lead",
                "phone": "+1 555 0100",
                "company_id": self.company.id,
            }
        )
        with self.assertRaises(ValidationError):
            self.env["crm.lead"].create(
                {
                    "name": "Second Lead",
                    "phone": "+1 555 0100",
                    "company_id": self.company.id,
                }
            )

    def test_different_email_is_allowed(self):
        self.env["crm.lead"].create(
            {
                "name": "First Lead",
                "email_from": "buyer@acme.example",
                "company_id": self.company.id,
            }
        )
        lead = self.env["crm.lead"].create(
            {
                "name": "Second Lead",
                "email_from": "other-buyer@acme.example",
                "company_id": self.company.id,
            }
        )
        self.assertTrue(lead)

    def test_duplicate_in_other_company_is_allowed(self):
        other_company = self.env["res.company"].create(
            {"name": "Dedupe Test Client", "parent_id": self.company.id}
        )
        self.env["crm.lead"].create(
            {
                "name": "First Lead",
                "email_from": "buyer@acme.example",
                "company_id": self.company.id,
            }
        )
        lead = self.env["crm.lead"].create(
            {
                "name": "Same Email, Other Company",
                "email_from": "buyer@acme.example",
                "company_id": other_company.id,
            }
        )
        self.assertTrue(lead)

    def test_lost_lead_does_not_block_new_one(self):
        first = self.env["crm.lead"].create(
            {
                "name": "First Lead",
                "email_from": "buyer@acme.example",
                "company_id": self.company.id,
            }
        )
        first.action_set_lost()
        lead = self.env["crm.lead"].create(
            {
                "name": "Second Lead",
                "email_from": "buyer@acme.example",
                "company_id": self.company.id,
            }
        )
        self.assertTrue(lead)
