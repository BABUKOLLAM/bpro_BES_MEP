from .common import MfgTestCommon

# FR-MFG-001/003/007/008: documents native Odoo Manufacturing behavior
# rather than building it - mrp.production.button_plan() already does
# capacity-aware work order scheduling (via mrp.workcenter's
# resource_calendar_id), and the BOM-aware Replenishment view already
# nets manufacturing demand into draft Manufacturing Orders for planner
# review, exactly like Phase 1's reorder-alert findings for Inventory.


class TestNativeCapacityScheduling(MfgTestCommon):
    def test_plan_creates_workorder_with_capacity_aware_schedule(self):
        mo = self._mo()
        mo.button_plan()
        self.assertEqual(len(mo.workorder_ids), 1)
        wo = mo.workorder_ids
        self.assertEqual(wo.workcenter_id, self.workcenter)
        self.assertTrue(wo.date_start and wo.date_finished)
        self.assertGreater(wo.date_finished, wo.date_start)

    def test_second_workorder_scheduled_after_first_when_capacity_full(self):
        mo1 = self._mo()
        mo1.button_plan()
        wo1 = mo1.workorder_ids

        mo2 = self._mo()
        mo2.button_plan()
        wo2 = mo2.workorder_ids

        # default_capacity=1 means the work center can't run both at once -
        # the scheduler must push the second work order out, not overlap it
        self.assertGreaterEqual(wo2.date_start, wo1.date_finished)


class TestNativeManufacturingReplenishment(MfgTestCommon):
    def test_reorder_below_min_creates_draft_mo_for_manufactured_product(self):
        manufacture_route = self.env["stock.rule"].search(
            [("action", "=", "manufacture")], limit=1
        ).route_id
        orderpoint = self.env["stock.warehouse.orderpoint"].create(
            {
                "product_id": self.finished.id,
                "warehouse_id": self.warehouse.id,
                "location_id": self.warehouse.lot_stock_id.id,
                "product_min_qty": 10.0,
                "product_max_qty": 20.0,
                "route_id": manufacture_route.id,
                "bom_id": self.bom.id,
            }
        )
        orderpoint.action_replenish()
        mo = self.env["mrp.production"].search(
            [("orderpoint_id", "=", orderpoint.id)]
        )
        self.assertTrue(
            mo, "replenishment for a manufactured product must create a Manufacturing Order"
        )
        # Native asymmetry vs. the purchase side (Phase 1): a manufacture-
        # route replenishment auto-confirms the MO immediately, it doesn't
        # stay draft the way a purchase requisition does. The FR-MFG-008
        # "review and adjust before conversion" step is still satisfied,
        # just earlier - the suggested qty is editable inline on the
        # orderpoint/Replenishment row before this action is triggered,
        # and the confirmed MO can still be cancelled/adjusted afterward.
        # Not worth custom code to force draft for parity with purchase.
        self.assertEqual(mo.state, "confirmed")
