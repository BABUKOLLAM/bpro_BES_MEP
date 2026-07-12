from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase


class TestStockAdjustmentApproval(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.location = cls.env["stock.location"].create(
            {"name": "Test Bin", "usage": "internal", "company_id": cls.company.id}
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Approval Test Widget",
                "is_storable": True,
                "standard_price": 100.0,
            }
        )
        # value threshold: adjustments worth more than 500 need approval
        cls.env["bpro.policy"].create(
            {
                "company_id": cls.company.id,
                "key": "stock_adjustment_value",
                "numeric_value": 500.0,
            }
        )
        cls.env["stock.quant"]._update_available_quantity(
            cls.product, cls.location, 10.0
        )
        cls.stock_manager = cls.env["res.users"].create(
            {
                "name": "Stock Manager",
                "login": "stock-manager@test.example",
                "email": "stock-manager@test.example",
                "groups_id": [
                    (4, cls.env.ref("base.group_user").id),
                    (4, cls.env.ref("stock.group_stock_manager").id),
                ],
            }
        )
        cls.stock_user = cls.env["res.users"].create(
            {
                "name": "Stock User",
                "login": "stock-user@test.example",
                "email": "stock-user@test.example",
                "groups_id": [
                    (4, cls.env.ref("base.group_user").id),
                    (4, cls.env.ref("stock.group_stock_user").id),
                ],
            }
        )

    def _quant(self):
        return self.env["stock.quant"]._gather(self.product, self.location, strict=True)

    def test_small_adjustment_applies_immediately(self):
        quant = self._quant()
        # 10 -> 12, diff 2 units x 100 = 200, under the 500 threshold
        quant.write({"inventory_quantity": 12.0, "bpro_adjustment_reason": "cycle count"})
        quant.action_apply_inventory()
        self.assertEqual(quant.quantity, 12.0)
        self.assertEqual(quant.approval_state, "none")

    def test_adjustment_without_reason_is_rejected(self):
        quant = self._quant()
        quant.write({"inventory_quantity": 12.0})
        with self.assertRaises(UserError):
            quant.action_apply_inventory()

    def test_large_adjustment_blocks_pending_approval(self):
        quant = self._quant()
        # 10 -> 20, diff 10 units x 100 = 1000, over the 500 threshold
        quant.write({"inventory_quantity": 20.0, "bpro_adjustment_reason": "large variance"})
        quant.action_apply_inventory()
        self.assertEqual(
            quant.quantity, 10.0, "on-hand quantity must not change until approved"
        )
        self.assertEqual(quant.approval_state, "pending")
        self.assertTrue(
            quant.activity_ids, "an approval activity must be scheduled for the manager"
        )

    def test_manager_approval_applies_the_adjustment(self):
        quant = self._quant()
        quant.write({"inventory_quantity": 20.0, "bpro_adjustment_reason": "large variance"})
        quant.action_apply_inventory()
        quant.with_user(self.stock_manager).action_approve()
        self.assertEqual(quant.quantity, 20.0)
        self.assertEqual(quant.approval_state, "none")
        move = self.env["stock.move"].search(
            [("product_id", "=", self.product.id), ("bpro_adjustment_reason", "!=", False)],
            limit=1,
            order="id desc",
        )
        self.assertEqual(move.bpro_adjustment_reason, "large variance")
        self.assertEqual(move.bpro_before_qty, 10.0)
        self.assertEqual(move.bpro_after_qty, 20.0)

    def test_non_manager_cannot_approve(self):
        quant = self._quant()
        quant.write({"inventory_quantity": 20.0, "bpro_adjustment_reason": "large variance"})
        quant.action_apply_inventory()
        with self.assertRaises(AccessError):
            quant.with_user(self.stock_user).action_approve()

    def test_threshold_uses_the_records_own_company_not_the_acting_users(self):
        """_approval_threshold_exceeded() must compare against the
        quant's own company_id's policy, not self.env.company (the
        acting user's active company) - otherwise a back-office user
        whose session company differs from the record's company gets
        the wrong threshold entirely."""
        other_company = self.env["res.company"].create(
            {"name": "Other Adjustment Co", "parent_id": self.company.id}
        )
        # a much lower threshold than the main company's 500 configured above
        self.env["bpro.policy"].create(
            {
                "company_id": other_company.id,
                "key": "stock_adjustment_value",
                "numeric_value": 50.0,
            }
        )
        other_location = self.env["stock.location"].create(
            {"name": "Other Co Bin", "usage": "internal", "company_id": other_company.id}
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product, other_location, 10.0
        )
        quant = self.env["stock.quant"]._gather(
            self.product, other_location, strict=True
        )
        self.assertEqual(self.env.company, self.company, "acting user stays on the main company")
        # 10 -> 12, diff 2 units x 100 = 200: under the main company's 500
        # threshold, but over other_company's own 50 threshold
        quant.write({"inventory_quantity": 12.0, "bpro_adjustment_reason": "cycle count"})
        quant.action_apply_inventory()
        self.assertEqual(
            quant.approval_state,
            "pending",
            "must use other_company's own 50 threshold, not the acting user's "
            "main-company 500 threshold",
        )

    def test_non_manager_cannot_bypass_approve_button_with_a_direct_write(self):
        """action_approve()'s approver check must be enforced at write()
        itself, not only inside the button method — otherwise any user
        with ordinary write access to stock.quant could skip the button
        and set approval_state='approved' directly."""
        quant = self._quant()
        quant.write({"inventory_quantity": 20.0, "bpro_adjustment_reason": "large variance"})
        quant.action_apply_inventory()
        with self.assertRaises(AccessError):
            quant.with_user(self.stock_user).write({"approval_state": "approved"})
        self.assertEqual(
            quant.quantity, 10.0, "a blocked bypass write must not apply the adjustment"
        )

    def test_first_ever_stock_count_with_reason_succeeds(self):
        # A product/location with zero prior on-hand has no existing quant
        # row - the "Update Quantity" screen must create one and let the
        # reason be set in the same flow, exactly like the fixed
        # view_stock_quant_tree_editable_bpro view now exposes.
        new_location = self.env["stock.location"].create(
            {"name": "Fresh Bin", "usage": "internal", "company_id": self.company.id}
        )
        quant = self.env["stock.quant"].create(
            {
                "product_id": self.product.id,
                "location_id": new_location.id,
                "inventory_quantity": 5.0,
                "bpro_adjustment_reason": "initial stock load",
            }
        )
        quant.action_apply_inventory()
        self.assertEqual(quant.quantity, 5.0)
        self.assertEqual(quant.approval_state, "none")

    def test_rejection_discards_the_count(self):
        quant = self._quant()
        quant.write({"inventory_quantity": 20.0, "bpro_adjustment_reason": "large variance"})
        quant.action_apply_inventory()
        quant.with_user(self.stock_manager).action_reject(reason="miscount, recount needed")
        self.assertEqual(
            quant.quantity, 10.0, "on-hand quantity must be untouched by a rejection"
        )
        self.assertEqual(quant.approval_state, "rejected")
        self.assertEqual(
            quant.inventory_quantity,
            0.0,
            "the discarded count is cleared (native action_clear_inventory_quantity "
            "behavior), forcing a fresh recount rather than silently keeping a stale one",
        )
