from odoo.tests.common import TransactionCase


class FinanceTestCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.env["account.chart.template"].try_loading(
            "generic_coa", cls.company, install_demo=False
        )
        cls.customer = cls.env["res.partner"].create({"name": "Finance Test Customer"})
        cls.vendor = cls.env["res.partner"].create({"name": "Finance Test Vendor"})
        cls.product = cls.env["product.product"].create(
            {"name": "Finance Test Product", "list_price": 100.0}
        )

    def _post_customer_invoice(self, amount, invoice_date, due_date=None):
        # date must be set explicitly - it does NOT reliably auto-sync from
        # invoice_date when creating via the ORM directly (only the UI's
        # onchange does that), and this module's KPI/report code filters
        # on date, not invoice_date.
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.customer.id,
                "invoice_date": invoice_date,
                "date": invoice_date,
                "invoice_date_due": due_date or invoice_date,
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
