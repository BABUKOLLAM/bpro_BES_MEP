from psycopg2 import IntegrityError

from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestCommission(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.product = cls.env["product.product"].create(
            {"name": "Commission Test Widget", "list_price": 100.0}
        )
        cls.partner = cls.env["res.partner"].create({"name": "Commission Test Customer"})
        cls.salesperson = cls.env["res.users"].create(
            {
                "name": "Commission Salesperson",
                "login": "commission-rep@test.example",
                "email": "commission-rep@test.example",
                "groups_id": [(4, cls.env.ref("base.group_user").id)],
            }
        )

    def _order(self, qty=1):
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "user_id": self.salesperson.id,
                "order_line": [
                    (0, 0, {"product_id": self.product.id, "product_uom_qty": qty})
                ],
            }
        )

    def test_no_rate_configured_gives_zero_commission(self):
        order = self._order()
        order.action_confirm()
        self.assertEqual(order.bpro_commission_pct, 0.0)
        self.assertEqual(order.bpro_commission_amount, 0.0)

    def test_company_default_policy_rate_applies(self):
        self.env["bpro.policy"].create(
            {
                "company_id": self.company.id,
                "key": "default_commission_pct",
                "numeric_value": 5.0,
            }
        )
        order = self._order()
        order.action_confirm()
        self.assertEqual(order.bpro_commission_pct, 5.0)
        self.assertEqual(order.bpro_commission_amount, order.amount_untaxed * 0.05)

    def test_per_salesperson_rate_overrides_company_default(self):
        self.env["bpro.policy"].create(
            {
                "company_id": self.company.id,
                "key": "default_commission_pct",
                "numeric_value": 5.0,
            }
        )
        self.env["bpro.commission.rate"].create(
            {
                "company_id": self.company.id,
                "user_id": self.salesperson.id,
                "commission_pct": 8.0,
            }
        )
        order = self._order()
        order.action_confirm()
        self.assertEqual(order.bpro_commission_pct, 8.0)

    def test_commission_is_frozen_at_confirmation_not_recomputed(self):
        rate = self.env["bpro.commission.rate"].create(
            {
                "company_id": self.company.id,
                "user_id": self.salesperson.id,
                "commission_pct": 8.0,
            }
        )
        order = self._order()
        order.action_confirm()
        rate.commission_pct = 15.0
        self.assertEqual(
            order.bpro_commission_pct,
            8.0,
            "a later rate change must not retroactively alter an already-confirmed order",
        )

    def test_only_one_rate_per_salesperson_per_company(self):
        self.env["bpro.commission.rate"].create(
            {
                "company_id": self.company.id,
                "user_id": self.salesperson.id,
                "commission_pct": 8.0,
            }
        )
        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"):
            self.env["bpro.commission.rate"].create(
                {
                    "company_id": self.company.id,
                    "user_id": self.salesperson.id,
                    "commission_pct": 10.0,
                }
            )
