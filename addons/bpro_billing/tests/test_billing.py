from datetime import date

from dateutil.relativedelta import relativedelta

from odoo.tests.common import TransactionCase


class TestBilling(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.corp = cls.env.ref("base.main_company")
        cls.env["account.chart.template"].try_loading(
            "generic_coa", cls.corp, install_demo=False
        )
        cls.client = cls.env["res.company"].create(
            {"name": "Billing Test Client", "parent_id": cls.corp.id}
        )
        for n in range(3):
            cls.env["hr.employee"].create(
                {"name": f"bill-emp-{n}", "company_id": cls.client.id}
            )
        cls.plan = cls.env["bpro.billing.plan"].create(
            {"name": "Test Plan", "price_per_seat": 100.0, "period": "monthly"}
        )
        cls.sub = cls.env["bpro.billing.subscription"].create(
            {"client_company_id": cls.client.id, "plan_id": cls.plan.id}
        )

    def test_seats_and_amount(self):
        self.assertEqual(self.sub.seats, 3)
        self.assertEqual(self.sub.amount, 300.0)

    def test_invoice_generation_rolls_date(self):
        start = self.sub.next_invoice_date
        self.sub._create_period_invoice()
        invoice = self.env["account.move"].search(
            [("bpro_subscription_id", "=", self.sub.id)]
        )
        self.assertEqual(len(invoice), 1)
        self.assertEqual(invoice.state, "draft")
        self.assertEqual(invoice.amount_untaxed, 300.0)
        self.assertEqual(self.sub.state, "active")
        self.assertEqual(
            self.sub.next_invoice_date, start + relativedelta(months=1)
        )

    def test_cron_only_invoices_due_subscriptions(self):
        self.sub.next_invoice_date = date.today() + relativedelta(days=10)
        self.env["bpro.billing.subscription"]._cron_generate_invoices()
        self.assertFalse(
            self.env["account.move"].search(
                [("bpro_subscription_id", "=", self.sub.id)]
            ),
            "a subscription due in the future must not be invoiced",
        )

    def test_cancelled_subscription_not_invoiced(self):
        self.sub.action_cancel()
        self.sub._create_period_invoice()
        self.assertFalse(
            self.env["account.move"].search(
                [("bpro_subscription_id", "=", self.sub.id)]
            )
        )
