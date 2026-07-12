from odoo import fields
from odoo.tests.common import TransactionCase


class TestReorderLevels(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.company.id)], limit=1
        )
        cls.env["bpro.policy"].create(
            {
                "company_id": cls.company.id,
                "key": "reorder_lead_time_days",
                "numeric_value": 10.0,
            }
        )
        cls.env["bpro.policy"].create(
            {
                "company_id": cls.company.id,
                "key": "reorder_safety_stock_pct",
                "numeric_value": 0.0,
            }
        )
        cls.env["bpro.policy"].create(
            {
                "company_id": cls.company.id,
                "key": "reorder_replenishment_cycle_days",
                "numeric_value": 30.0,
            }
        )

    def _orderpoint(self, product, lookback_days=90):
        return self.env["stock.warehouse.orderpoint"].create(
            {
                "product_id": product.id,
                "location_id": self.warehouse.lot_stock_id.id,
                "warehouse_id": self.warehouse.id,
                "bpro_lookback_days": lookback_days,
            }
        )

    def _deliver_to_customer(self, product, qty):
        self.env["stock.quant"]._update_available_quantity(
            product, self.warehouse.lot_stock_id, qty
        )
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.warehouse.out_type_id.id,
                "location_id": self.warehouse.lot_stock_id.id,
                "location_dest_id": self.env.ref("stock.stock_location_customers").id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "name": product.name,
                            "product_id": product.id,
                            "product_uom_qty": qty,
                            "product_uom": product.uom_id.id,
                            "location_id": self.warehouse.lot_stock_id.id,
                            "location_dest_id": self.env.ref(
                                "stock.stock_location_customers"
                            ).id,
                        },
                    )
                ],
            }
        )
        picking.action_confirm()
        picking.action_assign()
        picking.move_ids.quantity = qty
        picking.move_ids.picked = True
        picking.button_validate()
        return picking.move_ids

    def _consume_in_production(self, component, qty):
        workcenter = self.env["mrp.workcenter"].create(
            {"name": "Reorder Test Workcenter %s" % component.id}
        )
        finished = self.env["product.product"].create(
            {"name": "Reorder Test Finished for %s" % component.name, "is_storable": True}
        )
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": finished.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [
                    (0, 0, {"product_id": component.id, "product_qty": 1.0})
                ],
                "operation_ids": [
                    (0, 0, {"name": "Assemble", "workcenter_id": workcenter.id})
                ],
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            component, self.warehouse.lot_stock_id, qty + 10.0
        )
        mo = self.env["mrp.production"].create(
            {
                "product_id": finished.id,
                "product_qty": qty,
                "bom_id": bom.id,
                "product_uom_id": finished.uom_id.id,
            }
        )
        mo.action_confirm()
        mo.move_raw_ids.quantity = qty
        mo.move_raw_ids.picked = True
        mo.qty_producing = qty
        mo.move_finished_ids.quantity = qty
        mo.move_finished_ids.picked = True
        mo.button_mark_done()
        return mo

    def test_no_history_gives_zero_demand_and_zero_suggestion(self):
        product = self.env["product.product"].create(
            {"name": "Reorder Test No History", "is_storable": True}
        )
        orderpoint = self._orderpoint(product)
        self.assertEqual(orderpoint.bpro_avg_daily_demand, 0.0)
        self.assertEqual(orderpoint.bpro_suggested_min_qty, 0.0)
        self.assertEqual(orderpoint.bpro_suggested_max_qty, 0.0)

    def test_sales_demand_drives_avg_daily_demand(self):
        product = self.env["product.product"].create(
            {"name": "Reorder Test Sales Product", "is_storable": True}
        )
        self._deliver_to_customer(product, 90.0)
        orderpoint = self._orderpoint(product, lookback_days=90)
        self.assertEqual(orderpoint.bpro_avg_daily_demand, 1.0)

    def test_demand_does_not_leak_across_companies(self):
        """Deliveries of a product shared across companies (same
        product.product with no company restriction) must not inflate a
        different company's reorder-level suggestion - the underlying
        stock.move search must scope by the orderpoint's own company_id."""
        product = self.env["product.product"].create(
            {"name": "Reorder Test Cross-Company Product", "is_storable": True}
        )
        self._deliver_to_customer(product, 90.0)  # demand booked under self.company

        other_company = self.env["res.company"].create(
            {"name": "Other Reorder Co", "parent_id": self.company.id}
        )
        other_warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", other_company.id)], limit=1
        )
        other_orderpoint = self.env["stock.warehouse.orderpoint"].create(
            {
                "product_id": product.id,
                "company_id": other_company.id,
                "location_id": other_warehouse.lot_stock_id.id,
                "warehouse_id": other_warehouse.id,
                "bpro_lookback_days": 90,
            }
        )
        self.assertEqual(
            other_orderpoint.bpro_avg_daily_demand,
            0.0,
            "other_company has shipped none of this product - the main "
            "company's demand must not leak into its suggestion",
        )

    def test_production_consumption_drives_avg_daily_demand(self):
        component = self.env["product.product"].create(
            {"name": "Reorder Test Component", "is_storable": True}
        )
        self._consume_in_production(component, 90.0)
        orderpoint = self._orderpoint(component, lookback_days=90)
        self.assertEqual(orderpoint.bpro_avg_daily_demand, 1.0)

    def test_sales_and_consumption_add_together(self):
        # a product that is both sold directly AND consumed as a BOM
        # component elsewhere - its reorder demand must reflect both flows
        product = self.env["product.product"].create(
            {"name": "Reorder Test Dual Use Product", "is_storable": True}
        )
        self._deliver_to_customer(product, 45.0)
        self._consume_in_production(product, 45.0)
        orderpoint = self._orderpoint(product, lookback_days=90)
        self.assertEqual(orderpoint.bpro_avg_daily_demand, 1.0)

    def test_move_outside_lookback_window_is_excluded(self):
        product = self.env["product.product"].create(
            {"name": "Reorder Test Old Move Product", "is_storable": True}
        )
        moves = self._deliver_to_customer(product, 90.0)
        old_date = fields.Datetime.subtract(fields.Datetime.now(), days=200)
        moves.write({"date": old_date})
        orderpoint = self._orderpoint(product, lookback_days=90)
        self.assertEqual(orderpoint.bpro_avg_daily_demand, 0.0)

    def test_suggested_levels_use_policy_configured_parameters(self):
        product = self.env["product.product"].create(
            {"name": "Reorder Test Policy Product", "is_storable": True}
        )
        self._deliver_to_customer(product, 90.0)
        orderpoint = self._orderpoint(product, lookback_days=90)
        # avg_daily_demand = 1.0; lead_time=10, safety=0%, cycle=30
        self.assertEqual(orderpoint.bpro_suggested_min_qty, 10.0)
        self.assertEqual(orderpoint.bpro_suggested_max_qty, 40.0)

    def test_apply_suggested_levels_writes_into_native_fields(self):
        product = self.env["product.product"].create(
            {"name": "Reorder Test Apply Product", "is_storable": True}
        )
        self._deliver_to_customer(product, 90.0)
        orderpoint = self._orderpoint(product, lookback_days=90)
        orderpoint.action_bpro_apply_suggested_levels()
        self.assertEqual(orderpoint.product_min_qty, 10.0)
        self.assertEqual(orderpoint.product_max_qty, 40.0)
