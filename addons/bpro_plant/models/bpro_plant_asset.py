from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class BproPlantAsset(models.Model):
    _name = "bpro.plant.asset"
    _description = "Plant & Machinery Fixed Asset"

    name = fields.Char(required=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    equipment_id = fields.Many2one("maintenance.equipment", string="Equipment")
    workcenter_id = fields.Many2one("mrp.workcenter", string="Work Center")
    acquisition_date = fields.Date(required=True)
    acquisition_cost = fields.Monetary(required=True)
    salvage_value = fields.Monetary(default=0.0)
    useful_life_months = fields.Integer(required=True)
    depreciation_expense_account_id = fields.Many2one(
        "account.account", string="Depreciation Expense Account", required=True
    )
    accumulated_depreciation_account_id = fields.Many2one(
        "account.account", string="Accumulated Depreciation Account", required=True
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("running", "Depreciating"),
            ("fully_depreciated", "Fully Depreciated"),
        ],
        default="draft",
        required=True,
        copy=False,
    )
    depreciation_line_ids = fields.One2many(
        "bpro.plant.asset.depreciation.line", "asset_id", string="Depreciation Schedule"
    )
    monthly_depreciation = fields.Monetary(compute="_compute_monthly_depreciation")
    accumulated_depreciation = fields.Monetary(compute="_compute_accumulated_depreciation")
    book_value = fields.Monetary(compute="_compute_book_value")

    @api.depends("acquisition_cost", "salvage_value", "useful_life_months")
    def _compute_monthly_depreciation(self):
        for asset in self:
            if asset.useful_life_months:
                asset.monthly_depreciation = (
                    asset.acquisition_cost - asset.salvage_value
                ) / asset.useful_life_months
            else:
                asset.monthly_depreciation = 0.0

    @api.depends("depreciation_line_ids.state", "depreciation_line_ids.amount")
    def _compute_accumulated_depreciation(self):
        for asset in self:
            asset.accumulated_depreciation = sum(
                asset.depreciation_line_ids.filtered(
                    lambda line: line.state == "posted"
                ).mapped("amount")
            )

    @api.depends("acquisition_cost", "accumulated_depreciation")
    def _compute_book_value(self):
        for asset in self:
            asset.book_value = asset.acquisition_cost - asset.accumulated_depreciation

    def action_confirm(self):
        for asset in self.filtered(
            lambda a: a.state == "draft" and not a.depreciation_line_ids
        ):
            total = asset.acquisition_cost - asset.salvage_value
            monthly = (
                round(total / asset.useful_life_months, 2)
                if asset.useful_life_months
                else 0.0
            )
            running_total = 0.0
            lines = []
            for i in range(1, asset.useful_life_months + 1):
                period_date = asset.acquisition_date + relativedelta(months=i)
                if i == asset.useful_life_months:
                    # last line absorbs rounding so the schedule sums exactly
                    # to (acquisition_cost - salvage_value), not slightly off
                    amount = round(total - running_total, 2)
                else:
                    amount = monthly
                running_total += amount
                lines.append((0, 0, {"period_date": period_date, "amount": amount}))
            asset.write({"depreciation_line_ids": lines, "state": "running"})
