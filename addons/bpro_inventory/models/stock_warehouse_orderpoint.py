from odoo import api, fields, models

DEFAULT_LOOKBACK_DAYS = 90


class StockWarehouseOrderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    # Native reordering rules (product_min_qty/product_max_qty) are purely
    # static - there is no built-in way to derive them from historical
    # demand. This computes a suggested level from actual outbound flow
    # over a lookback window: customer deliveries (sales demand) for
    # products sold directly, and raw-material consumption in
    # manufacturing (production demand) for BOM components - added
    # together, since a product can be both sold and internally consumed.
    bpro_lookback_days = fields.Integer(default=DEFAULT_LOOKBACK_DAYS, required=True)
    bpro_avg_daily_demand = fields.Float(
        compute="_compute_bpro_avg_daily_demand",
        digits="Product Unit of Measure",
        help="(Customer deliveries + production consumption) over the "
        "lookback window, divided by the window length.",
    )
    bpro_suggested_min_qty = fields.Float(
        compute="_compute_bpro_suggested_levels", digits="Product Unit of Measure"
    )
    bpro_suggested_max_qty = fields.Float(
        compute="_compute_bpro_suggested_levels", digits="Product Unit of Measure"
    )

    @api.depends("product_id", "bpro_lookback_days")
    def _compute_bpro_avg_daily_demand(self):
        Move = self.env["stock.move"]
        for orderpoint in self:
            if not orderpoint.product_id or orderpoint.bpro_lookback_days <= 0:
                orderpoint.bpro_avg_daily_demand = 0.0
                continue
            since = fields.Datetime.subtract(
                fields.Datetime.now(), days=orderpoint.bpro_lookback_days
            )
            domain = [
                ("product_id", "=", orderpoint.product_id.id),
                ("company_id", "=", (orderpoint.company_id or self.env.company).id),
                ("state", "=", "done"),
                ("date", ">=", since),
            ]
            sales_moves = Move.search(
                domain + [("location_dest_id.usage", "=", "customer")]
            )
            consumption_moves = Move.search(
                domain + [("raw_material_production_id", "!=", False)]
            )
            total_demand = sum(sales_moves.mapped("quantity")) + sum(
                consumption_moves.mapped("quantity")
            )
            orderpoint.bpro_avg_daily_demand = (
                total_demand / orderpoint.bpro_lookback_days
            )

    @api.depends("bpro_avg_daily_demand", "company_id")
    def _compute_bpro_suggested_levels(self):
        Policy = self.env["bpro.policy"]
        for orderpoint in self:
            company = orderpoint.company_id or self.env.company
            lead_time_days = Policy.get_value(
                company, "reorder_lead_time_days", default=7.0
            )
            safety_stock_pct = Policy.get_value(
                company, "reorder_safety_stock_pct", default=20.0
            )
            cycle_days = Policy.get_value(
                company, "reorder_replenishment_cycle_days", default=30.0
            )
            demand = orderpoint.bpro_avg_daily_demand
            suggested_min = demand * lead_time_days * (1 + safety_stock_pct / 100.0)
            orderpoint.bpro_suggested_min_qty = suggested_min
            orderpoint.bpro_suggested_max_qty = suggested_min + demand * cycle_days

    def action_bpro_apply_suggested_levels(self):
        for orderpoint in self:
            orderpoint.write(
                {
                    "product_min_qty": orderpoint.bpro_suggested_min_qty,
                    "product_max_qty": orderpoint.bpro_suggested_max_qty,
                }
            )
