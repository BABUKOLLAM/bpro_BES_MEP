from collections import defaultdict

from odoo import api, fields, models

CURRENT_ASSET_TYPES = ("asset_cash", "asset_receivable", "asset_current", "asset_prepayments")
CURRENT_LIABILITY_TYPES = ("liability_payable", "liability_credit_card", "liability_current")


class BproFinanceDashboard(models.TransientModel):
    _name = "bpro.finance.dashboard"
    _description = "Financial Dashboard"

    as_of_date = fields.Date(default=fields.Date.context_today, required=True)
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id
    )
    cash_position = fields.Monetary(compute="_compute_kpis")
    total_receivables = fields.Monetary(compute="_compute_kpis")
    total_payables = fields.Monetary(compute="_compute_kpis")
    current_ratio = fields.Float(compute="_compute_kpis", digits=(16, 2))

    @api.depends("as_of_date")
    def _compute_kpis(self):
        for rec in self:
            data = self._get_kpi_data(self.env.company, rec.as_of_date)
            rec.cash_position = data["cash_position"]
            rec.total_receivables = data["total_receivables"]
            rec.total_payables = data["total_payables"]
            rec.current_ratio = data["current_ratio"]

    @api.model
    def _get_kpi_data(self, company, as_of_date):
        """Plain @api.model method, directly unit testable. Balance sign
        convention: Odoo's account.move.line.balance is debit - credit, so
        asset balances are naturally positive and liability balances are
        naturally negative - liabilities are negated below to report a
        positive 'amount owed'."""
        move_lines = self.env["account.move.line"].search(
            [
                ("company_id", "=", company.id),
                ("parent_state", "=", "posted"),
                ("date", "<=", as_of_date),
            ]
        )
        balances = defaultdict(float)
        for line in move_lines:
            balances[line.account_id.account_type] += line.balance

        cash = balances.get("asset_cash", 0.0)
        receivable = balances.get("asset_receivable", 0.0)
        current_assets = sum(balances.get(t, 0.0) for t in CURRENT_ASSET_TYPES)
        current_liabilities = -sum(balances.get(t, 0.0) for t in CURRENT_LIABILITY_TYPES)

        return {
            "cash_position": cash,
            "total_receivables": receivable,
            "total_payables": -balances.get("liability_payable", 0.0),
            "current_ratio": (
                current_assets / current_liabilities if current_liabilities else 0.0
            ),
        }
