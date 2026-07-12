from datetime import datetime, time

from odoo import api, fields, models


class BproExecutiveDashboard(models.TransientModel):
    _name = "bpro.executive.dashboard"
    _description = "Executive Dashboard"

    as_of_date = fields.Date(default=fields.Date.context_today, required=True)
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id
    )

    sales_mtd_revenue = fields.Monetary(compute="_compute_kpis")
    mfg_avg_variance_pct = fields.Float(compute="_compute_kpis", digits=(16, 2))
    inventory_pending_adjustments = fields.Integer(compute="_compute_kpis")
    cash_position = fields.Monetary(compute="_compute_kpis")
    total_receivables = fields.Monetary(compute="_compute_kpis")
    total_payables = fields.Monetary(compute="_compute_kpis")
    current_ratio = fields.Float(compute="_compute_kpis", digits=(16, 2))
    hr_pending_expense_approvals = fields.Integer(compute="_compute_kpis")
    logistics_on_time_pct = fields.Float(compute="_compute_kpis", digits=(16, 2))
    quality_pass_rate_pct = fields.Float(compute="_compute_kpis", digits=(16, 2))
    plant_total_asset_book_value = fields.Monetary(compute="_compute_kpis")
    project_pending_budget_approvals = fields.Integer(compute="_compute_kpis")
    fleet_trip_cost = fields.Monetary(compute="_compute_kpis")

    @api.depends("as_of_date")
    def _compute_kpis(self):
        for rec in self:
            data = self._get_kpi_data(self.env.company, rec.as_of_date)
            for field_name, value in data.items():
                rec[field_name] = value

    @api.model
    def _get_kpi_data(self, company, as_of_date):
        """Plain @api.model method, directly unit testable. Blends
        month-to-date "flow" metrics (Sales, Manufacturing, Logistics -
        modules with a clean business date) with right-now "stock"
        metrics (Inventory, HR, Project backlogs; Plant book value) and
        all-time cumulative metrics (Quality, Fleet - avoids fragile
        date-boundary handling on less clean date fields)."""
        month_start = as_of_date.replace(day=1)
        month_start_dt = datetime.combine(month_start, time.min)
        as_of_dt = datetime.combine(as_of_date, time.max)
        data = {}

        orders = self.env["sale.order"].search(
            [
                ("company_id", "=", company.id),
                ("state", "=", "sale"),
                ("date_order", ">=", month_start_dt),
                ("date_order", "<=", as_of_dt),
            ]
        )
        # amount_total is in each order's own transaction currency (which
        # can differ from the company's - see this engagement's per-
        # document INR pricelist for a company whose own base currency is
        # USD) - convert before summing, not after, or a mixed-currency
        # month's total is simply wrong, not just mislabeled.
        data["sales_mtd_revenue"] = sum(
            order.currency_id._convert(
                order.amount_total, company.currency_id, company, as_of_date
            )
            for order in orders
        )

        workorders = self.env["mrp.workorder"].search(
            [
                ("company_id", "=", company.id),
                ("state", "=", "done"),
                ("date_finished", ">=", month_start_dt),
                ("date_finished", "<=", as_of_dt),
            ]
        )
        data["mfg_avg_variance_pct"] = (
            sum(workorders.mapped("bpro_variance_pct")) / len(workorders)
            if workorders
            else 0.0
        )

        data["inventory_pending_adjustments"] = self.env["stock.quant"].search_count(
            [("company_id", "=", company.id), ("approval_state", "=", "pending")]
        )

        finance_data = self.env["bpro.finance.dashboard"]._get_kpi_data(
            company, as_of_date
        )
        data["cash_position"] = finance_data["cash_position"]
        data["total_receivables"] = finance_data["total_receivables"]
        data["total_payables"] = finance_data["total_payables"]
        data["current_ratio"] = finance_data["current_ratio"]

        data["hr_pending_expense_approvals"] = self.env[
            "hr.expense.sheet"
        ].search_count(
            [
                ("company_id", "=", company.id),
                ("bpro_finance_approval_state", "=", "pending"),
            ]
        )

        receipts = self.env["stock.picking"].search(
            [
                ("company_id", "=", company.id),
                ("state", "=", "done"),
                ("purchase_id", "!=", False),
                ("date_done", ">=", month_start_dt),
                ("date_done", "<=", as_of_dt),
            ]
        )
        data["logistics_on_time_pct"] = (
            len(receipts.filtered("bpro_on_time")) / len(receipts) * 100.0
            if receipts
            else 0.0
        )

        checks = self.env["bpro.quality.check"].search(
            [("company_id", "=", company.id), ("result", "in", ("pass", "fail"))]
        )
        data["quality_pass_rate_pct"] = (
            len(checks.filtered(lambda c: c.result == "pass")) / len(checks) * 100.0
            if checks
            else 0.0
        )

        assets = self.env["bpro.plant.asset"].search(
            [("company_id", "=", company.id), ("state", "=", "running")]
        )
        data["plant_total_asset_book_value"] = sum(assets.mapped("book_value"))

        data["project_pending_budget_approvals"] = self.env[
            "project.task"
        ].search_count(
            [("company_id", "=", company.id), ("approval_state", "=", "pending")]
        )

        batches = self.env["stock.picking.batch"].search(
            [
                ("company_id", "=", company.id),
                ("state", "=", "done"),
                ("vehicle_id", "!=", False),
            ]
        )
        data["fleet_trip_cost"] = sum(batches.mapped("bpro_trip_cost"))

        return data
