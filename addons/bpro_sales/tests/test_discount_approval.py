from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestDiscountApproval(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.env["bpro.policy"].create(
            {
                "company_id": cls.company.id,
                "key": "sales_discount_pct",
                "numeric_value": 10.0,
            }
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Discount Test Widget", "list_price": 100.0}
        )
        cls.partner = cls.env["res.partner"].create({"name": "Discount Test Customer"})
        cls.sales_manager = cls.env["res.users"].create(
            {
                "name": "Sales Manager",
                "login": "sales-manager@test.example",
                "email": "sales-manager@test.example",
                "groups_id": [
                    (4, cls.env.ref("base.group_user").id),
                    (4, cls.env.ref("sales_team.group_sale_manager").id),
                ],
            }
        )

    def _order(self, discount):
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 1,
                            "discount": discount,
                        },
                    )
                ],
            }
        )

    def test_small_discount_confirms_without_approval(self):
        order = self._order(5.0)
        order.action_confirm()
        self.assertEqual(order.state, "sale")
        self.assertEqual(order.approval_state, "none")

    def test_large_discount_blocks_confirm(self):
        order = self._order(20.0)
        with self.assertRaises(UserError):
            order.action_confirm()
        self.assertEqual(order.state, "draft")
        self.assertEqual(order.approval_state, "pending")

    def test_manager_approval_unblocks_confirm(self):
        order = self._order(20.0)
        with self.assertRaises(UserError):
            order.action_confirm()
        order.with_user(self.sales_manager).action_approve()
        order.action_confirm()
        self.assertEqual(order.state, "sale")

    def test_increasing_discount_after_approval_reopens_the_gate(self):
        order = self._order(20.0)
        with self.assertRaises(UserError):
            order.action_confirm()
        order.with_user(self.sales_manager).action_approve()
        # rep bumps the discount further after approval - must not sail
        # through on the stale "approved" state
        order.order_line.discount = 30.0
        # still over threshold, so the reset immediately re-requests
        # approval as part of this same save - not left dangling at "none"
        self.assertEqual(order.approval_state, "pending")
        with self.assertRaises(UserError):
            order.action_confirm()
