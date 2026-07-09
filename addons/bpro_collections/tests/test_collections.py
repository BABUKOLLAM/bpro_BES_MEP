from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestCollections(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["account.chart.template"].try_loading(
            "generic_coa", cls.env.company, install_demo=False
        )
        cls.customer = cls.env["res.partner"].create({"name": "Collections Test Dealer"})
        cls.env["bpro.policy"].create(
            [
                {
                    "company_id": cls.env.company.id,
                    "key": "collections_level1_days",
                    "numeric_value": 15,
                },
                {
                    "company_id": cls.env.company.id,
                    "key": "collections_level2_days",
                    "numeric_value": 30,
                },
                {
                    "company_id": cls.env.company.id,
                    "key": "collections_level3_days",
                    "numeric_value": 60,
                },
            ]
        )

    def _overdue_invoice(self, days_overdue, amount=10000.0):
        invoice_date = fields.Date.today() - timedelta(days=days_overdue + 30)
        due_date = fields.Date.today() - timedelta(days=days_overdue)
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.customer.id,
                "invoice_date": invoice_date,
                "date": invoice_date,
                "invoice_date_due": due_date,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Test line",
                            "quantity": 1,
                            "price_unit": amount,
                            "tax_ids": False,
                        },
                    )
                ],
            }
        )
        move.action_post()
        return move

    def test_no_case_below_grace_period(self):
        self._overdue_invoice(days_overdue=5)
        self.env["bpro.collections.case"]._bpro_sync_cases(self.env.company)
        case = self.env["bpro.collections.case"].search(
            [("partner_id", "=", self.customer.id)]
        )
        self.assertFalse(case)

    def test_case_opened_past_grace_period_at_reminder_level(self):
        self._overdue_invoice(days_overdue=20)
        self.env["bpro.collections.case"]._bpro_sync_cases(self.env.company)
        case = self.env["bpro.collections.case"].search(
            [("partner_id", "=", self.customer.id)]
        )
        self.assertTrue(case)
        self.assertEqual(case.level, "reminder")
        self.assertEqual(case.state, "open")

    def test_case_escalates_to_firm(self):
        self._overdue_invoice(days_overdue=45)
        self.env["bpro.collections.case"]._bpro_sync_cases(self.env.company)
        case = self.env["bpro.collections.case"].search(
            [("partner_id", "=", self.customer.id)]
        )
        self.assertEqual(case.level, "firm")

    def test_case_escalates_to_final(self):
        self._overdue_invoice(days_overdue=75)
        self.env["bpro.collections.case"]._bpro_sync_cases(self.env.company)
        case = self.env["bpro.collections.case"].search(
            [("partner_id", "=", self.customer.id)]
        )
        self.assertEqual(case.level, "final")

    def test_paying_the_invoice_closes_the_case(self):
        move = self._overdue_invoice(days_overdue=20)
        self.env["bpro.collections.case"]._bpro_sync_cases(self.env.company)
        case = self.env["bpro.collections.case"].search(
            [("partner_id", "=", self.customer.id)]
        )
        self.assertEqual(case.state, "open")

        payment = self.env["account.payment"].create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": self.customer.id,
                "amount": move.amount_total,
            }
        )
        payment.action_post()
        (move.line_ids + payment.move_id.line_ids).filtered(
            lambda l: l.account_id.account_type == "asset_receivable" and not l.reconciled
        ).reconcile()

        self.env["bpro.collections.case"]._bpro_sync_cases(self.env.company)
        case = self.env["bpro.collections.case"].search(
            [("partner_id", "=", self.customer.id)]
        )
        self.assertEqual(case.state, "closed")

    def test_record_contact_schedules_next_action(self):
        self._overdue_invoice(days_overdue=20)
        self.env["bpro.collections.case"]._bpro_sync_cases(self.env.company)
        case = self.env["bpro.collections.case"].search(
            [("partner_id", "=", self.customer.id)]
        )
        case.action_record_contact()
        self.assertTrue(case.last_contacted_date)
        self.assertTrue(case.next_action_date)
        self.assertEqual(
            (case.next_action_date - case.last_contacted_date).days, 7
        )
