from collections import defaultdict
from datetime import timedelta

from odoo import api, fields, models

ASSET_CURRENT_TYPES = ("asset_current", "asset_cash", "asset_receivable", "asset_prepayments")
ASSET_NONCURRENT_TYPES = ("asset_fixed", "asset_non_current")
LIABILITY_CURRENT_TYPES = ("liability_current", "liability_payable", "liability_credit_card")
LIABILITY_NONCURRENT_TYPES = ("liability_non_current",)
EQUITY_TYPES = ("equity", "equity_unaffected")
INCOME_TYPES = ("income", "income_other")
EXPENSE_TYPES = ("expense", "expense_direct_cost")
DEPRECIATION_TYPES = ("expense_depreciation",)
OTHER_CURRENT_ASSET_TYPES = ("asset_current", "asset_prepayments")
OTHER_CURRENT_LIABILITY_TYPES = ("liability_current", "liability_credit_card")


class BproFinancialReportMixin(models.AbstractModel):
    _name = "bpro.financial.report.mixin"
    _description = "Shared balance-computation helpers for financial statement reports"

    @api.model
    def _type_balance(self, company, types, date_from=None, date_to=None):
        """Sum of account.move.line.balance (debit - credit) for posted
        entries on accounts of the given account_type(s), optionally
        bounded by date. Naturally-debit accounts (assets, expenses) come
        out positive; naturally-credit accounts (liabilities, equity,
        income) come out negative - callers negate where a positive
        'amount owed'/'amount earned' figure is wanted."""
        domain = [
            ("company_id", "=", company.id),
            ("parent_state", "=", "posted"),
            ("account_id.account_type", "in", list(types)),
        ]
        if date_from:
            domain.append(("date", ">=", date_from))
        if date_to:
            domain.append(("date", "<=", date_to))
        lines = self.env["account.move.line"].search(domain)
        return sum(lines.mapped("balance"))

    @api.model
    def _net_profit(self, company, date_from=None, date_to=None):
        """Positive = profit for the given period (or since inception, if
        date_from is omitted)."""
        income = self._type_balance(company, INCOME_TYPES, date_from, date_to)
        expense = self._type_balance(
            company, EXPENSE_TYPES + DEPRECIATION_TYPES, date_from, date_to
        )
        return -income - expense

    @api.model
    def _depreciation(self, company, date_from=None, date_to=None):
        return self._type_balance(company, DEPRECIATION_TYPES, date_from, date_to)

    @api.model
    def _delta(self, company, types, date_from, date_to):
        """Change in a type-bucket's balance between the day before
        date_from (opening) and date_to (closing)."""
        day_before = date_from - timedelta(days=1)
        closing = self._type_balance(company, types, date_to=date_to)
        opening = self._type_balance(company, types, date_to=day_before)
        return closing - opening


# ---------------------------------------------------------------------------
# Trial Balance
# ---------------------------------------------------------------------------
class BproTrialBalanceWizard(models.TransientModel):
    _name = "bpro.trial.balance.wizard"
    _inherit = ["bpro.financial.report.mixin"]
    _description = "Trial Balance"

    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True, default=fields.Date.context_today)
    line_ids = fields.One2many("bpro.trial.balance.line", "wizard_id", readonly=True)
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id
    )
    total_opening_debit = fields.Monetary(compute="_compute_totals")
    total_opening_credit = fields.Monetary(compute="_compute_totals")
    total_debit = fields.Monetary(compute="_compute_totals")
    total_credit = fields.Monetary(compute="_compute_totals")
    total_closing_debit = fields.Monetary(compute="_compute_totals")
    total_closing_credit = fields.Monetary(compute="_compute_totals")

    @api.depends(
        "line_ids.opening_debit", "line_ids.opening_credit",
        "line_ids.debit", "line_ids.credit",
        "line_ids.closing_debit", "line_ids.closing_credit",
    )
    def _compute_totals(self):
        for rec in self:
            rec.total_opening_debit = sum(rec.line_ids.mapped("opening_debit"))
            rec.total_opening_credit = sum(rec.line_ids.mapped("opening_credit"))
            rec.total_debit = sum(rec.line_ids.mapped("debit"))
            rec.total_credit = sum(rec.line_ids.mapped("credit"))
            rec.total_closing_debit = sum(rec.line_ids.mapped("closing_debit"))
            rec.total_closing_credit = sum(rec.line_ids.mapped("closing_credit"))

    def action_generate(self):
        self.ensure_one()
        self.line_ids.unlink()
        data = self._get_trial_balance_data(self.env.company, self.date_from, self.date_to)
        self.line_ids = [(0, 0, vals) for vals in data]
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.model
    def _get_trial_balance_data(self, company, date_from, date_to):
        accounts = self.env["account.account"].search([("company_ids", "in", company.id)])
        lines = self.env["account.move.line"].search(
            [
                ("company_id", "=", company.id),
                ("parent_state", "=", "posted"),
                ("account_id", "in", accounts.ids),
                ("date", "<=", date_to),
            ]
        )
        opening = defaultdict(float)
        period_debit = defaultdict(float)
        period_credit = defaultdict(float)
        for line in lines:
            if line.date < date_from:
                opening[line.account_id.id] += line.balance
            else:
                period_debit[line.account_id.id] += line.debit
                period_credit[line.account_id.id] += line.credit

        result = []
        for acc in accounts:
            op = opening[acc.id]
            pd = period_debit[acc.id]
            pc = period_credit[acc.id]
            closing = op + pd - pc
            if not (op or pd or pc):
                continue
            result.append(
                {
                    "account_id": acc.id,
                    "opening_debit": op if op > 0 else 0.0,
                    "opening_credit": -op if op < 0 else 0.0,
                    "debit": pd,
                    "credit": pc,
                    "closing_debit": closing if closing > 0 else 0.0,
                    "closing_credit": -closing if closing < 0 else 0.0,
                }
            )
        return result


class BproTrialBalanceLine(models.TransientModel):
    _name = "bpro.trial.balance.line"
    _description = "Trial Balance Line"
    _order = "id"

    wizard_id = fields.Many2one("bpro.trial.balance.wizard", required=True, ondelete="cascade")
    account_id = fields.Many2one("account.account", required=True)
    currency_id = fields.Many2one(related="wizard_id.currency_id")
    opening_debit = fields.Monetary()
    opening_credit = fields.Monetary()
    debit = fields.Monetary()
    credit = fields.Monetary()
    closing_debit = fields.Monetary()
    closing_credit = fields.Monetary()


# ---------------------------------------------------------------------------
# Balance Sheet
# ---------------------------------------------------------------------------
class BproBalanceSheetWizard(models.TransientModel):
    _name = "bpro.balance.sheet.wizard"
    _inherit = ["bpro.financial.report.mixin"]
    _description = "Balance Sheet"

    date_to = fields.Date(required=True, default=fields.Date.context_today)
    line_ids = fields.One2many("bpro.balance.sheet.line", "wizard_id", readonly=True)
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id
    )
    total_assets = fields.Monetary(readonly=True)
    total_liabilities_equity = fields.Monetary(readonly=True)
    balance_check = fields.Monetary(
        readonly=True, help="Total Assets minus (Total Liabilities + Equity). Must be 0.00."
    )

    def action_generate(self):
        self.ensure_one()
        self.line_ids.unlink()
        data = self._get_balance_sheet_data(self.env.company, self.date_to)
        self.line_ids = [(0, 0, vals) for vals in data["lines"]]
        self.total_assets = data["total_assets"]
        self.total_liabilities_equity = data["total_liabilities_equity"]
        self.balance_check = data["total_assets"] - data["total_liabilities_equity"]
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.model
    def _get_balance_sheet_data(self, company, date_to):
        fixed_assets = self._type_balance(company, ASSET_NONCURRENT_TYPES, date_to=date_to)
        current_assets = self._type_balance(company, ASSET_CURRENT_TYPES, date_to=date_to)
        total_assets = fixed_assets + current_assets

        current_liab = -self._type_balance(company, LIABILITY_CURRENT_TYPES, date_to=date_to)
        noncurrent_liab = -self._type_balance(
            company, LIABILITY_NONCURRENT_TYPES, date_to=date_to
        )
        equity = -self._type_balance(company, EQUITY_TYPES, date_to=date_to)
        net_profit = self._net_profit(company, date_to=date_to)
        total_liabilities_equity = current_liab + noncurrent_liab + equity + net_profit

        lines = [
            {"sequence": 1, "label": "ASSETS", "amount": 0.0, "is_header": True},
            {"sequence": 2, "label": "Non-current assets", "amount": fixed_assets},
            {"sequence": 3, "label": "Current assets", "amount": current_assets},
            {"sequence": 4, "label": "Total Assets", "amount": total_assets, "is_total": True},
            {"sequence": 5, "label": "EQUITY AND LIABILITIES", "amount": 0.0, "is_header": True},
            {"sequence": 6, "label": "Shareholders' Equity", "amount": equity},
            {"sequence": 7, "label": "Profit / (Loss) carried forward", "amount": net_profit},
            {"sequence": 8, "label": "Non-current liabilities", "amount": noncurrent_liab},
            {"sequence": 9, "label": "Current liabilities", "amount": current_liab},
            {
                "sequence": 10,
                "label": "Total Equity and Liabilities",
                "amount": total_liabilities_equity,
                "is_total": True,
            },
        ]
        return {
            "lines": lines,
            "total_assets": total_assets,
            "total_liabilities_equity": total_liabilities_equity,
        }


class BproBalanceSheetLine(models.TransientModel):
    _name = "bpro.balance.sheet.line"
    _description = "Balance Sheet Line"
    _order = "sequence"

    wizard_id = fields.Many2one("bpro.balance.sheet.wizard", required=True, ondelete="cascade")
    currency_id = fields.Many2one(related="wizard_id.currency_id")
    sequence = fields.Integer()
    label = fields.Char(required=True)
    amount = fields.Monetary()
    is_header = fields.Boolean()
    is_total = fields.Boolean()


# ---------------------------------------------------------------------------
# Profit & Loss
# ---------------------------------------------------------------------------
class BproProfitLossWizard(models.TransientModel):
    _name = "bpro.profit.loss.wizard"
    _inherit = ["bpro.financial.report.mixin"]
    _description = "Profit and Loss Statement"

    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True, default=fields.Date.context_today)
    line_ids = fields.One2many("bpro.profit.loss.line", "wizard_id", readonly=True)
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id
    )
    total_income = fields.Monetary(readonly=True)
    total_expense = fields.Monetary(readonly=True)
    net_profit = fields.Monetary(readonly=True)

    def action_generate(self):
        self.ensure_one()
        self.line_ids.unlink()
        data = self._get_pl_data(self.env.company, self.date_from, self.date_to)
        self.line_ids = [(0, 0, vals) for vals in data["lines"]]
        self.total_income = data["total_income"]
        self.total_expense = data["total_expense"]
        self.net_profit = data["net_profit"]
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.model
    def _get_pl_data(self, company, date_from, date_to):
        pl_types = INCOME_TYPES + EXPENSE_TYPES + DEPRECIATION_TYPES
        accounts = self.env["account.account"].search(
            [("company_ids", "in", company.id), ("account_type", "in", list(pl_types))]
        )
        move_lines = self.env["account.move.line"].search(
            [
                ("company_id", "=", company.id),
                ("parent_state", "=", "posted"),
                ("account_id", "in", accounts.ids),
                ("date", ">=", date_from),
                ("date", "<=", date_to),
            ]
        )
        by_account = defaultdict(float)
        for line in move_lines:
            by_account[line.account_id] += line.balance

        lines = []
        total_income = 0.0
        total_expense = 0.0
        for acc, bal in by_account.items():
            if not bal:
                continue
            if acc.account_type in INCOME_TYPES:
                amt = -bal
                total_income += amt
                lines.append({"account_id": acc.id, "amount": amt, "section": "income"})
            else:
                amt = bal
                total_expense += amt
                lines.append({"account_id": acc.id, "amount": amt, "section": "expense"})
        return {
            "lines": lines,
            "total_income": total_income,
            "total_expense": total_expense,
            "net_profit": total_income - total_expense,
        }


class BproProfitLossLine(models.TransientModel):
    _name = "bpro.profit.loss.line"
    _description = "Profit and Loss Line"

    wizard_id = fields.Many2one("bpro.profit.loss.wizard", required=True, ondelete="cascade")
    currency_id = fields.Many2one(related="wizard_id.currency_id")
    account_id = fields.Many2one("account.account", required=True)
    amount = fields.Monetary()
    section = fields.Selection([("income", "Income"), ("expense", "Expense")], required=True)


# ---------------------------------------------------------------------------
# Cash Flow Statement (indirect method)
# ---------------------------------------------------------------------------
class BproCashFlowWizard(models.TransientModel):
    _name = "bpro.cash.flow.wizard"
    _inherit = ["bpro.financial.report.mixin"]
    _description = "Cash Flow Statement (Indirect Method)"

    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True, default=fields.Date.context_today)
    line_ids = fields.One2many("bpro.cash.flow.line", "wizard_id", readonly=True)
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id
    )
    net_increase_in_cash = fields.Monetary(readonly=True)
    actual_cash_movement = fields.Monetary(readonly=True)
    reconciliation_diff = fields.Monetary(
        readonly=True, help="net_increase_in_cash minus actual_cash_movement. Must be 0.00."
    )

    def action_generate(self):
        self.ensure_one()
        self.line_ids.unlink()
        data = self._get_cash_flow_data(self.env.company, self.date_from, self.date_to)
        self.line_ids = [(0, 0, vals) for vals in data["lines"]]
        self.net_increase_in_cash = data["net_increase_in_cash"]
        self.actual_cash_movement = data["actual_cash_movement"]
        self.reconciliation_diff = data["net_increase_in_cash"] - data["actual_cash_movement"]
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.model
    def _get_cash_flow_data(self, company, date_from, date_to):
        net_profit = self._net_profit(company, date_from, date_to)
        depreciation = self._depreciation(company, date_from, date_to)

        # Asset-type buckets carry a natural debit (positive raw) balance -
        # the raw delta already means "the asset amount increased by this
        # much", so it is used as-is.
        d_receivable = self._delta(company, ("asset_receivable",), date_from, date_to)
        d_other_cur_assets = self._delta(
            company, OTHER_CURRENT_ASSET_TYPES, date_from, date_to
        )
        d_fixed_assets = self._delta(company, ASSET_NONCURRENT_TYPES, date_from, date_to)
        # Liability/equity buckets carry a natural credit (negative raw)
        # balance, so the raw delta goes negative when the liability/equity
        # amount actually increases - negate it so a positive number here
        # means "the liability/equity amount increased".
        d_payable = -self._delta(company, ("liability_payable",), date_from, date_to)
        d_other_cur_liab = -self._delta(
            company, OTHER_CURRENT_LIABILITY_TYPES, date_from, date_to
        )
        d_equity = -self._delta(company, EQUITY_TYPES, date_from, date_to)
        d_noncurrent_liab = -self._delta(
            company, LIABILITY_NONCURRENT_TYPES, date_from, date_to
        )

        operating = (
            net_profit
            + depreciation
            - d_receivable
            - d_other_cur_assets
            + d_payable
            + d_other_cur_liab
        )
        # Gross capex estimate: net movement in fixed assets plus the
        # depreciation charged against them in the period (depreciation is
        # added back in Operating above, so grossing up Investing here by
        # the same amount avoids double-counting it in the total).
        investing = -(d_fixed_assets + depreciation)
        financing = d_equity + d_noncurrent_liab
        net_increase_in_cash = operating + investing + financing
        actual_cash_movement = self._delta(company, ("asset_cash",), date_from, date_to)

        lines = [
            {"sequence": 1, "section": "operating", "label": "Net Profit for the period", "amount": net_profit},
            {"sequence": 2, "section": "operating", "label": "Add: Depreciation", "amount": depreciation},
            {"sequence": 3, "section": "operating", "label": "(Increase) / Decrease in Receivables", "amount": -d_receivable},
            {"sequence": 4, "section": "operating", "label": "(Increase) / Decrease in Other Current Assets", "amount": -d_other_cur_assets},
            {"sequence": 5, "section": "operating", "label": "Increase / (Decrease) in Payables", "amount": d_payable},
            {"sequence": 6, "section": "operating", "label": "Increase / (Decrease) in Other Current Liabilities", "amount": d_other_cur_liab},
            {"sequence": 7, "section": "operating", "label": "Net Cash from Operating Activities", "amount": operating, "is_total": True},
            {"sequence": 8, "section": "investing", "label": "Purchase of Fixed Assets (net of depreciation)", "amount": investing},
            {"sequence": 9, "section": "investing", "label": "Net Cash from Investing Activities", "amount": investing, "is_total": True},
            {"sequence": 10, "section": "financing", "label": "Capital Introduced / (Withdrawn)", "amount": d_equity},
            {"sequence": 11, "section": "financing", "label": "Long-term Borrowings Raised / (Repaid)", "amount": d_noncurrent_liab},
            {"sequence": 12, "section": "financing", "label": "Net Cash from Financing Activities", "amount": financing, "is_total": True},
            {"sequence": 13, "section": "summary", "label": "Net Increase / (Decrease) in Cash", "amount": net_increase_in_cash, "is_total": True},
            {"sequence": 14, "section": "summary", "label": "Actual Cash & Bank Movement (reconciliation check)", "amount": actual_cash_movement},
        ]
        return {
            "lines": lines,
            "net_increase_in_cash": net_increase_in_cash,
            "actual_cash_movement": actual_cash_movement,
        }


class BproCashFlowLine(models.TransientModel):
    _name = "bpro.cash.flow.line"
    _description = "Cash Flow Statement Line"
    _order = "sequence"

    wizard_id = fields.Many2one("bpro.cash.flow.wizard", required=True, ondelete="cascade")
    currency_id = fields.Many2one(related="wizard_id.currency_id")
    sequence = fields.Integer()
    section = fields.Selection(
        [
            ("operating", "Operating Activities"),
            ("investing", "Investing Activities"),
            ("financing", "Financing Activities"),
            ("summary", "Summary"),
        ],
        required=True,
    )
    label = fields.Char(required=True)
    amount = fields.Monetary()
    is_total = fields.Boolean()


# ---------------------------------------------------------------------------
# Fund Flow Statement
# ---------------------------------------------------------------------------
class BproFundFlowWizard(models.TransientModel):
    _name = "bpro.fund.flow.wizard"
    _inherit = ["bpro.financial.report.mixin"]
    _description = "Fund Flow Statement"

    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True, default=fields.Date.context_today)
    line_ids = fields.One2many("bpro.fund.flow.line", "wizard_id", readonly=True)
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id
    )
    net_increase_in_working_capital = fields.Monetary(readonly=True)
    working_capital_schedule_check = fields.Monetary(readonly=True)
    reconciliation_diff = fields.Monetary(
        readonly=True,
        help="Fund-flow-derived working capital change minus the schedule "
        "total computed directly from current accounts. Must be 0.00.",
    )

    def action_generate(self):
        self.ensure_one()
        self.line_ids.unlink()
        data = self._get_fund_flow_data(self.env.company, self.date_from, self.date_to)
        self.line_ids = [(0, 0, vals) for vals in data["lines"]]
        self.net_increase_in_working_capital = data["net_increase_in_working_capital"]
        self.working_capital_schedule_check = data["working_capital_schedule_check"]
        self.reconciliation_diff = (
            data["net_increase_in_working_capital"] - data["working_capital_schedule_check"]
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.model
    def _get_fund_flow_data(self, company, date_from, date_to):
        net_profit = self._net_profit(company, date_from, date_to)
        depreciation = self._depreciation(company, date_from, date_to)
        funds_from_operations = net_profit + depreciation

        d_fixed = self._delta(company, ASSET_NONCURRENT_TYPES, date_from, date_to)
        # Liability/equity buckets are natural-credit (negative raw balance);
        # negate so a positive number means the liability/equity itself grew.
        d_noncurrent_liab = -self._delta(
            company, LIABILITY_NONCURRENT_TYPES, date_from, date_to
        )
        d_equity = -self._delta(company, EQUITY_TYPES, date_from, date_to)

        # Gross up the fixed-asset movement by the depreciation charged
        # against it in the period - depreciation is already inside
        # "funds_from_operations" above, so without this adjustment it would
        # be counted twice (once as an operations add-back, once again as
        # an implicit "disposal" showing up in the raw net fixed-asset
        # delta). A positive value here is a net application (real capex
        # beyond depreciation); negative is a net source (net disposal).
        fixed_asset_effect = -(d_fixed + depreciation)

        sources = funds_from_operations
        applications = 0.0
        fixed_asset_line = None
        if fixed_asset_effect < 0:
            applications += -fixed_asset_effect
            fixed_asset_line = ("application", "Purchase of Fixed Assets (net of depreciation)", -fixed_asset_effect)
        elif fixed_asset_effect > 0:
            sources += fixed_asset_effect
            fixed_asset_line = ("source", "Sale of Fixed Assets (net of depreciation)", fixed_asset_effect)

        loan_line = None
        if d_noncurrent_liab > 0:
            sources += d_noncurrent_liab
            loan_line = ("source", "Long-term Borrowings Raised", d_noncurrent_liab)
        elif d_noncurrent_liab < 0:
            applications += -d_noncurrent_liab
            loan_line = ("application", "Long-term Borrowings Repaid", -d_noncurrent_liab)

        equity_line = None
        if d_equity > 0:
            sources += d_equity
            equity_line = ("source", "Capital Introduced", d_equity)
        elif d_equity < 0:
            applications += -d_equity
            equity_line = ("application", "Capital Withdrawn", -d_equity)

        net_increase_in_working_capital = sources - applications

        # Independent cross-check: Working Capital = Current Assets - Current
        # Liabilities, computed directly from the current accounts. Current
        # asset raw deltas are already "increase = positive"; current
        # liability raw deltas are natural-credit (negative when the
        # liability grows), and an increase in a liability REDUCES working
        # capital - both effects are captured correctly by a straight sum of
        # all five raw deltas with no sign-flipping needed.
        d_receivable = self._delta(company, ("asset_receivable",), date_from, date_to)
        d_other_cur_assets = self._delta(
            company, OTHER_CURRENT_ASSET_TYPES, date_from, date_to
        )
        d_cash = self._delta(company, ("asset_cash",), date_from, date_to)
        d_payable_raw = self._delta(company, ("liability_payable",), date_from, date_to)
        d_other_cur_liab_raw = self._delta(
            company, OTHER_CURRENT_LIABILITY_TYPES, date_from, date_to
        )
        working_capital_schedule_check = (
            d_receivable + d_other_cur_assets + d_cash + d_payable_raw + d_other_cur_liab_raw
        )

        lines = [
            {"sequence": 1, "section": "source", "label": "Funds from Operations (Net Profit + Depreciation)", "amount": funds_from_operations},
        ]
        seq = 2
        for entry in (fixed_asset_line, loan_line, equity_line):
            if entry:
                section, label, amount = entry
                lines.append({"sequence": seq, "section": section, "label": label, "amount": amount})
                seq += 1
        lines.append({"sequence": seq, "section": "total", "label": "Net Increase / (Decrease) in Working Capital", "amount": net_increase_in_working_capital, "is_total": True})
        seq += 1
        lines.append({"sequence": seq, "section": "schedule", "label": "Change in Receivables (WC impact)", "amount": d_receivable})
        seq += 1
        lines.append({"sequence": seq, "section": "schedule", "label": "Change in Other Current Assets (WC impact)", "amount": d_other_cur_assets})
        seq += 1
        lines.append({"sequence": seq, "section": "schedule", "label": "Change in Cash & Bank (WC impact)", "amount": d_cash})
        seq += 1
        lines.append({"sequence": seq, "section": "schedule", "label": "Change in Payables (WC impact)", "amount": d_payable_raw})
        seq += 1
        lines.append({"sequence": seq, "section": "schedule", "label": "Change in Other Current Liabilities (WC impact)", "amount": d_other_cur_liab_raw})
        seq += 1
        lines.append({"sequence": seq, "section": "schedule", "label": "Net Change in Working Capital (schedule total)", "amount": working_capital_schedule_check, "is_total": True})

        return {
            "lines": lines,
            "net_increase_in_working_capital": net_increase_in_working_capital,
            "working_capital_schedule_check": working_capital_schedule_check,
        }


class BproFundFlowLine(models.TransientModel):
    _name = "bpro.fund.flow.line"
    _description = "Fund Flow Statement Line"
    _order = "sequence"

    wizard_id = fields.Many2one("bpro.fund.flow.wizard", required=True, ondelete="cascade")
    currency_id = fields.Many2one(related="wizard_id.currency_id")
    sequence = fields.Integer()
    section = fields.Selection(
        [
            ("source", "Source of Funds"),
            ("application", "Application of Funds"),
            ("total", "Total"),
            ("schedule", "Working Capital Schedule"),
        ],
        required=True,
    )
    label = fields.Char(required=True)
    amount = fields.Monetary()
    is_total = fields.Boolean()
