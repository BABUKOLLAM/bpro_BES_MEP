from psycopg2 import IntegrityError

from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger

# bpro.approval.mixin is an AbstractModel with no table of its own, so its
# request/approve/reject flow is exercised end-to-end where it's actually
# used — the first concrete host model is bpro_inventory's stock-adjustment
# approval (Phase 1). This file only covers bpro.policy, the piece that is
# independently testable without a host model.


class TestBproPolicy(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.corp = cls.env.ref("base.main_company")
        cls.client = cls.env["res.company"].create(
            {"name": "Policy Test Client", "parent_id": cls.corp.id}
        )

    def test_get_value_returns_default_when_unset(self):
        Policy = self.env["bpro.policy"]
        self.assertEqual(
            Policy.get_value(self.client, "sales_discount_pct", default=10.0), 10.0
        )

    def test_get_value_returns_configured_value(self):
        self.env["bpro.policy"].create(
            {
                "company_id": self.client.id,
                "key": "sales_discount_pct",
                "numeric_value": 15.0,
            }
        )
        self.assertEqual(
            self.env["bpro.policy"].get_value(
                self.client, "sales_discount_pct", default=10.0
            ),
            15.0,
        )

    def test_get_value_is_scoped_per_company(self):
        other_client = self.env["res.company"].create(
            {"name": "Other Policy Client", "parent_id": self.corp.id}
        )
        self.env["bpro.policy"].create(
            {
                "company_id": self.client.id,
                "key": "sales_discount_pct",
                "numeric_value": 15.0,
            }
        )
        self.assertEqual(
            self.env["bpro.policy"].get_value(
                other_client, "sales_discount_pct", default=5.0
            ),
            5.0,
            "a policy set for one client must not leak to another",
        )

    def test_duplicate_key_per_company_is_rejected(self):
        self.env["bpro.policy"].create(
            {
                "company_id": self.client.id,
                "key": "sales_discount_pct",
                "numeric_value": 15.0,
            }
        )
        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"):
            self.env["bpro.policy"].create(
                {
                    "company_id": self.client.id,
                    "key": "sales_discount_pct",
                    "numeric_value": 20.0,
                }
            )
