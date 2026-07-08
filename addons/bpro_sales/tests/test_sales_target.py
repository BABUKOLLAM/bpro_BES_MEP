from datetime import date

from odoo.tests.common import TransactionCase


class TestSalesTarget(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.rep = cls.env["res.users"].create(
            {
                "name": "Target Test Rep",
                "login": "target-rep@test.example",
                "email": "target-rep@test.example",
                "groups_id": [
                    (4, cls.env.ref("base.group_user").id),
                    (4, cls.env.ref("sales_team.group_sale_salesman").id),
                ],
            }
        )
        cls.other_rep = cls.env["res.users"].create(
            {
                "name": "Other Rep",
                "login": "other-rep@test.example",
                "email": "other-rep@test.example",
                "groups_id": [
                    (4, cls.env.ref("base.group_user").id),
                    (4, cls.env.ref("sales_team.group_sale_salesman").id),
                ],
            }
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Target Test Widget", "list_price": 100.0}
        )
        cls.partner = cls.env["res.partner"].create({"name": "Target Test Customer"})

    def _confirmed_order(self, user, amount, order_date):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "user_id": user.id,
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
        order.date_order = order_date
        return order

    def test_actual_sums_only_this_rep_confirmed_orders_in_period(self):
        self._confirmed_order(self.rep, 3000.0, "2026-06-10 10:00:00")
        self._confirmed_order(self.rep, 2000.0, "2026-06-20 10:00:00")
        # outside the period - must not count
        self._confirmed_order(self.rep, 9999.0, "2026-07-01 10:00:00")
        # different rep - must not count
        self._confirmed_order(self.other_rep, 9999.0, "2026-06-15 10:00:00")

        target = self.env["bpro.sales.target"].create(
            {
                "user_id": self.rep.id,
                "date_from": date(2026, 6, 1),
                "date_to": date(2026, 6, 30),
                "target_amount": 10000.0,
            }
        )
        self.assertEqual(target.actual_amount, 5000.0)
        self.assertEqual(target.attainment_pct, 50.0)

    def test_draft_orders_are_not_counted(self):
        draft = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "user_id": self.rep.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 1,
                            "price_unit": 5000.0,
                            "tax_id": False,
                        },
                    )
                ],
            }
        )
        draft.date_order = "2026-06-10 10:00:00"
        target = self.env["bpro.sales.target"].create(
            {
                "user_id": self.rep.id,
                "date_from": date(2026, 6, 1),
                "date_to": date(2026, 6, 30),
                "target_amount": 10000.0,
            }
        )
        self.assertEqual(target.actual_amount, 0.0)
