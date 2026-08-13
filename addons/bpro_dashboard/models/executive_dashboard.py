from datetime import datetime, time, timedelta

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
    recruitment_open_vacancies = fields.Integer(compute="_compute_kpis")
    recruitment_overdue_joining_reports = fields.Integer(compute="_compute_kpis")
    hr_pending_attendance_exceptions = fields.Integer(compute="_compute_kpis")
    hr_open_exit_requests = fields.Integer(compute="_compute_kpis")
    hr_attrition_rate_pct = fields.Float(compute="_compute_kpis", digits=(16, 2))
    hr_el_liability = fields.Monetary(compute="_compute_kpis")

    # Weekly MIS: reproduces the "2026 ME Weekly Meet Report" ritual
    # (production/sales trend, item-wise achievement, area-wise sales)
    # from live transaction data instead of a hand-copied spreadsheet.
    weekly_production_qty = fields.Float(compute="_compute_weekly_mis", digits=(16, 2))
    production_wow_pct = fields.Float(compute="_compute_weekly_mis", digits=(16, 2))
    weekly_sales_amount = fields.Monetary(compute="_compute_weekly_mis")
    sales_wow_pct = fields.Float(compute="_compute_weekly_mis", digits=(16, 2))
    monthly_production_qty = fields.Float(compute="_compute_weekly_mis", digits=(16, 2))
    production_mom_pct = fields.Float(compute="_compute_weekly_mis", digits=(16, 2))
    monthly_sales_amount = fields.Monetary(compute="_compute_weekly_mis")
    sales_mom_pct = fields.Float(compute="_compute_weekly_mis", digits=(16, 2))
    item_production_ids = fields.One2many(
        "bpro.dashboard.item.production.line", "dashboard_id", compute="_compute_weekly_mis"
    )
    item_sales_ids = fields.One2many(
        "bpro.dashboard.item.sales.line", "dashboard_id", compute="_compute_weekly_mis"
    )
    area_sales_ids = fields.One2many(
        "bpro.dashboard.area.sales.line", "dashboard_id", compute="_compute_weekly_mis"
    )

    @api.depends("as_of_date")
    def _compute_kpis(self):
        for rec in self:
            data = self._get_kpi_data(self.env.company, rec.as_of_date)
            for field_name, value in data.items():
                rec[field_name] = value

    @api.depends("as_of_date")
    def _compute_weekly_mis(self):
        for rec in self:
            data = self._get_weekly_mis_data(self.env.company, rec.as_of_date)
            rec.weekly_production_qty = data["weekly_production_qty"]
            rec.production_wow_pct = data["production_wow_pct"]
            rec.weekly_sales_amount = data["weekly_sales_amount"]
            rec.sales_wow_pct = data["sales_wow_pct"]
            rec.monthly_production_qty = data["monthly_production_qty"]
            rec.production_mom_pct = data["production_mom_pct"]
            rec.monthly_sales_amount = data["monthly_sales_amount"]
            rec.sales_mom_pct = data["sales_mom_pct"]
            rec.item_production_ids = [(5, 0, 0)] + [
                (0, 0, line) for line in data["item_production_lines"]
            ]
            rec.item_sales_ids = [(5, 0, 0)] + [
                (0, 0, line) for line in data["item_sales_lines"]
            ]
            rec.area_sales_ids = [(5, 0, 0)] + [
                (0, 0, line) for line in data["area_sales_lines"]
            ]

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

        approved_requests = self.env["bpro.vacancy.request"].search(
            [("company_id", "=", company.id), ("state", "=", "approved")]
        )
        # "Open" = the linked hr.job still hasn't hired up to the
        # requested headcount - a request stays open until the vacancy
        # it created is actually filled, not merely approved.
        data["recruitment_open_vacancies"] = len(
            approved_requests.filtered(
                lambda r: r.job_id.no_of_hired_employee < r.job_id.no_of_recruitment
            )
        )

        data["recruitment_overdue_joining_reports"] = self.env[
            "bpro.joining.report"
        ].search_count(
            [
                ("employee_id.company_id", "=", company.id),
                ("state", "=", "pending"),
                ("sla_deadline", "<", as_of_date),
            ]
        )

        data["hr_pending_attendance_exceptions"] = self.env[
            "bpro.attendance.exception"
        ].search_count(
            [
                ("employee_id.company_id", "=", company.id),
                ("state", "=", "pending"),
            ]
        )

        data["hr_open_exit_requests"] = self.env["bpro.exit.request"].search_count(
            [
                ("company_id", "=", company.id),
                ("state", "in", ("submitted", "accepted", "settled")),
            ]
        )

        # Trailing-12-month attrition: closed exits with a last working
        # day in the window, over the CURRENT active headcount - a
        # deliberate simplification of the textbook average-headcount
        # denominator, which would need historical headcount snapshots
        # this system doesn't keep.
        headcount = self.env["hr.employee"].search_count(
            [("company_id", "=", company.id)]
        )
        exits_12m = self.env["bpro.exit.request"].search_count(
            [
                ("company_id", "=", company.id),
                ("state", "=", "closed"),
                ("last_working_day", ">", as_of_date - timedelta(days=365)),
                ("last_working_day", "<=", as_of_date),
            ]
        )
        data["hr_attrition_rate_pct"] = (
            exits_12m / headcount * 100.0 if headcount else 0.0
        )

        # EL encashment liability: the same s79(11) formula bpro_exit's
        # F&F uses (balance x Basic/26), summed over active employees -
        # so this figure and an actual settlement always agree.
        el_liability = 0.0
        el_type = self.env.ref("bpro_leave.leave_type_earned", raise_if_not_found=False)
        if el_type:
            allocations = self.env["hr.leave.allocation"].search([
                ("employee_id.company_id", "=", company.id),
                ("holiday_status_id", "=", el_type.id),
                ("state", "=", "validate"),
            ])
            taken = self.env["hr.leave"].search([
                ("employee_id.company_id", "=", company.id),
                ("holiday_status_id", "=", el_type.id),
                ("state", "=", "validate"),
            ])
            balance_by_employee = {}
            for allocation in allocations:
                balance_by_employee[allocation.employee_id] = (
                    balance_by_employee.get(allocation.employee_id, 0.0)
                    + allocation.number_of_days
                )
            for leave in taken:
                balance_by_employee[leave.employee_id] = (
                    balance_by_employee.get(leave.employee_id, 0.0)
                    - leave.number_of_days
                )
            for employee, balance in balance_by_employee.items():
                if balance <= 0:
                    continue
                contract = self.env["hr.contract"].search(
                    [("employee_id", "=", employee.id), ("state", "=", "open")],
                    limit=1,
                )
                if contract:
                    monthly_basic = (
                        contract.ctc_annual / 12.0 * (contract.basic_percent / 100.0)
                    )
                    el_liability += balance * monthly_basic / 26.0
        data["hr_el_liability"] = el_liability

        return data

    @api.model
    def _production_qty(self, company, start_dt, end_dt):
        workorders = self.env["mrp.workorder"].search(
            [
                ("company_id", "=", company.id),
                ("state", "=", "done"),
                ("date_finished", ">=", start_dt),
                ("date_finished", "<=", end_dt),
            ]
        )
        return sum(workorders.mapped("qty_produced")), workorders

    @api.model
    def _sales_amount(self, company, as_of_date, start_dt, end_dt):
        orders = self.env["sale.order"].search(
            [
                ("company_id", "=", company.id),
                ("state", "=", "sale"),
                ("date_order", ">=", start_dt),
                ("date_order", "<=", end_dt),
            ]
        )
        amount = sum(
            order.currency_id._convert(
                order.amount_total, company.currency_id, company, as_of_date
            )
            for order in orders
        )
        return amount, orders

    @api.model
    def _pct_change(self, current, previous):
        return ((current - previous) / previous * 100.0) if previous else 0.0

    @api.model
    def _get_weekly_mis_data(self, company, as_of_date):
        """Plain @api.model method, directly unit testable.

        Week = trailing 7 days ending on as_of_date (matches the source
        spreadsheet's own Friday-to-Friday weekly meeting cadence without
        assuming a fixed weekday). Month = month-to-date vs. the prior
        full calendar month, the same convention the client's own
        "Dashboard" tab uses for its MoM figures.
        """
        week_end = as_of_date
        week_start = week_end - timedelta(days=6)
        prev_week_end = week_start - timedelta(days=1)
        prev_week_start = prev_week_end - timedelta(days=6)

        month_start = as_of_date.replace(day=1)
        prev_month_end = month_start - timedelta(days=1)
        prev_month_start = prev_month_end.replace(day=1)

        def bounds(d1, d2):
            return datetime.combine(d1, time.min), datetime.combine(d2, time.max)

        week_dt = bounds(week_start, week_end)
        prev_week_dt = bounds(prev_week_start, prev_week_end)
        month_dt = bounds(month_start, as_of_date)
        prev_month_dt = bounds(prev_month_start, prev_month_end)

        data = {}

        weekly_qty, week_workorders = self._production_qty(company, *week_dt)
        prev_weekly_qty, _ = self._production_qty(company, *prev_week_dt)
        data["weekly_production_qty"] = weekly_qty
        data["production_wow_pct"] = self._pct_change(weekly_qty, prev_weekly_qty)

        monthly_qty, month_workorders = self._production_qty(company, *month_dt)
        prev_monthly_qty, _ = self._production_qty(company, *prev_month_dt)
        data["monthly_production_qty"] = monthly_qty
        data["production_mom_pct"] = self._pct_change(monthly_qty, prev_monthly_qty)

        weekly_sales, week_orders = self._sales_amount(company, as_of_date, *week_dt)
        prev_weekly_sales, _ = self._sales_amount(company, as_of_date, *prev_week_dt)
        data["weekly_sales_amount"] = weekly_sales
        data["sales_wow_pct"] = self._pct_change(weekly_sales, prev_weekly_sales)

        monthly_sales, _ = self._sales_amount(company, as_of_date, *month_dt)
        prev_monthly_sales, _ = self._sales_amount(company, as_of_date, *prev_month_dt)
        data["monthly_sales_amount"] = monthly_sales
        data["sales_mom_pct"] = self._pct_change(monthly_sales, prev_monthly_sales)

        targets = self.env["bpro.item.target"].search([("company_id", "=", company.id)])

        item_production_lines = []
        for target in targets.filtered("monthly_production_qty_target"):
            achieved = sum(
                month_workorders.filtered(
                    lambda w, p=target.product_id: w.product_id == p
                ).mapped("qty_produced")
            )
            balance = achieved - target.monthly_production_qty_target
            achievement_pct = (
                achieved / target.monthly_production_qty_target * 100.0
                if target.monthly_production_qty_target
                else 0.0
            )
            item_production_lines.append(
                {
                    "product_id": target.product_id.id,
                    "achieved": achieved,
                    "target": target.monthly_production_qty_target,
                    "balance": balance,
                    "achievement_pct": achievement_pct,
                }
            )
        data["item_production_lines"] = item_production_lines

        item_sales_lines = []
        for target in targets.filtered("weekly_sales_qty_target"):
            lines = self.env["sale.order.line"].search(
                [
                    ("order_id", "in", week_orders.ids),
                    ("product_id", "=", target.product_id.id),
                ]
            )
            actual = sum(lines.mapped("product_uom_qty"))
            diff = actual - target.weekly_sales_qty_target
            achievement_pct = (
                actual / target.weekly_sales_qty_target * 100.0
                if target.weekly_sales_qty_target
                else 0.0
            )
            item_sales_lines.append(
                {
                    "product_id": target.product_id.id,
                    "actual": actual,
                    "target": target.weekly_sales_qty_target,
                    "diff": diff,
                    "achievement_pct": achievement_pct,
                }
            )
        data["item_sales_lines"] = item_sales_lines

        area_sales_lines = []
        areas = self.env["bpro.sales.area"].search([("company_id", "=", company.id)])
        for area in areas:
            count = len(week_orders.filtered(lambda o, a=area: o.sales_area_id == a))
            if count:
                area_sales_lines.append({"sales_area_id": area.id, "order_count": count})
        data["area_sales_lines"] = area_sales_lines

        return data
