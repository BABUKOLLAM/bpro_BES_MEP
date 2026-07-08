from datetime import date

from .common import FinanceTestCommon


class TestFinanceDashboard(FinanceTestCommon):
    def _post_vendor_bill(self, amount, invoice_date):
        move = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.vendor.id,
                "invoice_date": invoice_date,
                "date": invoice_date,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
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

    def test_receivables_and_payables_reflect_open_balances(self):
        self._post_customer_invoice(1000.0, "2026-06-01", due_date="2026-06-01")
        self._post_vendor_bill(300.0, "2026-06-01")

        data = self.env["bpro.finance.dashboard"]._get_kpi_data(
            self.company, date(2026, 6, 15)
        )
        self.assertEqual(data["total_receivables"], 1000.0)
        self.assertEqual(data["total_payables"], 300.0)

    def test_current_ratio_is_assets_over_liabilities(self):
        self._post_customer_invoice(1000.0, "2026-06-01", due_date="2026-06-01")
        self._post_vendor_bill(500.0, "2026-06-01")

        data = self.env["bpro.finance.dashboard"]._get_kpi_data(
            self.company, date(2026, 6, 15)
        )
        # current assets include the 1000 receivable, current liabilities
        # the 500 payable -> ratio 2.0
        self.assertAlmostEqual(data["current_ratio"], 2.0, places=2)

    def test_zero_liabilities_does_not_divide_by_zero(self):
        self._post_customer_invoice(1000.0, "2026-06-01", due_date="2026-06-01")
        data = self.env["bpro.finance.dashboard"]._get_kpi_data(
            self.company, date(2026, 6, 15)
        )
        self.assertEqual(data["current_ratio"], 0.0)
