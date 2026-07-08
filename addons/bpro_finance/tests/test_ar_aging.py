from datetime import date

from .common import FinanceTestCommon


class TestArAging(FinanceTestCommon):
    def test_buckets_by_days_overdue(self):
        # due today -> current; 15 days overdue -> 1-30; 45 -> 31-60;
        # 75 -> 61-90; 120 -> 90+
        self._post_customer_invoice(1000.0, "2026-06-15", due_date="2026-06-15")
        self._post_customer_invoice(2000.0, "2026-05-31", due_date="2026-05-31")
        self._post_customer_invoice(3000.0, "2026-05-01", due_date="2026-05-01")
        self._post_customer_invoice(4000.0, "2026-04-01", due_date="2026-04-01")
        self._post_customer_invoice(5000.0, "2026-02-15", due_date="2026-02-15")

        as_of = date(2026, 6, 15)
        data = self.env["bpro.ar.aging.wizard"]._get_aging_data(self.company, as_of)
        self.assertEqual(len(data), 1, "all invoices belong to the same customer")
        line = data[0]
        self.assertEqual(line["current"], 1000.0)
        self.assertEqual(line["d1_30"], 2000.0)
        self.assertEqual(line["d31_60"], 3000.0)
        self.assertEqual(line["d61_90"], 4000.0)
        self.assertEqual(line["d90_plus"], 5000.0)
        self.assertEqual(line["total"], 15000.0)

    def test_paid_invoice_excluded(self):
        move = self._post_customer_invoice(1000.0, "2026-06-01", due_date="2026-06-01")
        payment = self.env["account.payment"].create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": self.customer.id,
                "amount": 1000.0,
                "date": "2026-06-10",
            }
        )
        payment.action_post()
        (move.line_ids + payment.move_id.line_ids).filtered(
            lambda l: l.account_id.account_type == "asset_receivable" and not l.reconciled
        ).reconcile()

        data = self.env["bpro.ar.aging.wizard"]._get_aging_data(
            self.company, date(2026, 6, 15)
        )
        self.assertFalse(data, "a fully paid invoice must not appear in the aging report")

    def test_partial_payment_shows_remaining_residual(self):
        move = self._post_customer_invoice(1000.0, "2026-06-01", due_date="2026-06-01")
        payment = self.env["account.payment"].create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": self.customer.id,
                "amount": 400.0,
                "date": "2026-06-10",
            }
        )
        payment.action_post()
        (move.line_ids + payment.move_id.line_ids).filtered(
            lambda l: l.account_id.account_type == "asset_receivable" and not l.reconciled
        ).reconcile()

        data = self.env["bpro.ar.aging.wizard"]._get_aging_data(
            self.company, date(2026, 6, 15)
        )
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["total"], 600.0)
