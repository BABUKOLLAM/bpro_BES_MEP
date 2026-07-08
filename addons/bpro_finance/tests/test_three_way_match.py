from odoo.exceptions import UserError

from .common import FinanceTestCommon


class TestThreeWayMatch(FinanceTestCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["bpro.policy"].create(
            {
                "company_id": cls.company.id,
                "key": "three_way_match_tolerance_pct",
                "numeric_value": 10.0,
            }
        )
        cls.stock_product = cls.env["product.product"].create(
            {"name": "3-Way Match Test Component", "is_storable": True}
        )
        cls.account_manager = cls.env["res.users"].create(
            {
                "name": "Account Manager",
                "login": "account-manager@test.example",
                "email": "account-manager@test.example",
                "groups_id": [
                    (4, cls.env.ref("base.group_user").id),
                    (4, cls.env.ref("account.group_account_manager").id),
                ],
            }
        )

    def _received_po(self, ordered_qty, received_qty, price_unit=50.0):
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.stock_product.id,
                            "product_qty": ordered_qty,
                            "price_unit": price_unit,
                        },
                    )
                ],
            }
        )
        po.button_confirm()
        picking = po.picking_ids
        picking.move_ids.quantity = received_qty
        picking.move_ids.picked = True
        picking.button_validate()
        return po

    def _bill(self, po, billed_qty, price_unit=None):
        return self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.vendor.id,
                "invoice_date": "2026-06-15",
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.stock_product.id,
                            "quantity": billed_qty,
                            "price_unit": price_unit or po.order_line.price_unit,
                            "purchase_line_id": po.order_line.id,
                            "tax_ids": False,
                        },
                    )
                ],
            }
        )

    def test_matching_bill_posts_without_approval(self):
        po = self._received_po(10.0, 10.0)
        bill = self._bill(po, 10.0)
        bill.action_post()
        self.assertEqual(bill.state, "posted")
        self.assertEqual(bill.approval_state, "none")

    def test_bill_within_tolerance_posts(self):
        po = self._received_po(10.0, 10.0)
        # 10.5 vs 10 received = 5% variance, under the 10% tolerance
        bill = self._bill(po, 10.5)
        bill.action_post()
        self.assertEqual(bill.state, "posted")

    def test_bill_exceeding_tolerance_blocks_and_requests_approval(self):
        po = self._received_po(10.0, 10.0)
        # 15 vs 10 received = 50% variance
        bill = self._bill(po, 15.0)
        with self.assertRaises(UserError):
            bill.action_post()
        self.assertEqual(bill.state, "draft")
        self.assertEqual(bill.approval_state, "pending")
        self.assertIn("15.0", bill.bpro_match_mismatch)

    def test_manager_approval_unblocks_posting(self):
        po = self._received_po(10.0, 10.0)
        bill = self._bill(po, 15.0)
        with self.assertRaises(UserError):
            bill.action_post()
        bill.with_user(self.account_manager).action_approve()
        bill.action_post()
        self.assertEqual(bill.state, "posted")

    def test_price_mismatch_also_triggers_approval(self):
        po = self._received_po(10.0, 10.0, price_unit=50.0)
        # correct qty, but price billed way above PO price
        bill = self._bill(po, 10.0, price_unit=100.0)
        with self.assertRaises(UserError):
            bill.action_post()
        self.assertEqual(bill.approval_state, "pending")
