from .common import FinanceTestCommon

# FR-FIN-001/003: documents native Odoo Accounting behavior rather than
# building it - invoicing a confirmed sales order and registering full or
# partial customer payments (with automatic invoice status transitions)
# are core Community features requiring no custom code.


class TestNativeInvoicingAndPayment(FinanceTestCommon):
    def _confirmed_order(self, amount):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.customer.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 1,
                            "price_unit": amount,
                            "tax_id": False,
                        },
                    )
                ],
            }
        )
        order.action_confirm()
        return order

    def test_invoice_generated_from_confirmed_order(self):
        order = self._confirmed_order(1000.0)
        invoice = order._create_invoices()
        invoice.action_post()
        self.assertEqual(invoice.move_type, "out_invoice")
        self.assertEqual(invoice.amount_total, 1000.0)
        self.assertEqual(invoice.invoice_origin, order.name)
        self.assertEqual(invoice.payment_state, "not_paid")

    def test_full_payment_marks_invoice_paid(self):
        order = self._confirmed_order(1000.0)
        invoice = order._create_invoices()
        invoice.action_post()

        payment = self.env["account.payment"].create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": self.customer.id,
                "amount": 1000.0,
            }
        )
        payment.action_post()
        (invoice.line_ids + payment.move_id.line_ids).filtered(
            lambda l: l.account_id.account_type == "asset_receivable" and not l.reconciled
        ).reconcile()

        self.assertEqual(invoice.payment_state, "paid")
        self.assertEqual(invoice.amount_residual, 0.0)

    def test_partial_payment_marks_invoice_partial(self):
        order = self._confirmed_order(1000.0)
        invoice = order._create_invoices()
        invoice.action_post()

        payment = self.env["account.payment"].create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": self.customer.id,
                "amount": 600.0,
            }
        )
        payment.action_post()
        (invoice.line_ids + payment.move_id.line_ids).filtered(
            lambda l: l.account_id.account_type == "asset_receivable" and not l.reconciled
        ).reconcile()

        self.assertEqual(invoice.payment_state, "partial")
        self.assertEqual(invoice.amount_residual, 400.0)
