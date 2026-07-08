from odoo import _, api, fields, models


class BproPlantAssetDepreciationLine(models.Model):
    _name = "bpro.plant.asset.depreciation.line"
    _description = "Plant Asset Depreciation Line"
    _order = "period_date"

    asset_id = fields.Many2one(
        "bpro.plant.asset", required=True, ondelete="cascade", index=True
    )
    period_date = fields.Date(required=True)
    amount = fields.Monetary(required=True, currency_field="currency_id")
    currency_id = fields.Many2one(related="asset_id.currency_id")
    state = fields.Selection(
        [("draft", "Draft"), ("posted", "Posted")], default="draft", required=True
    )
    move_id = fields.Many2one("account.move", readonly=True, copy=False)

    def _bpro_post(self):
        self.ensure_one()
        asset = self.asset_id
        journal = self.env["account.journal"].search(
            [("type", "=", "general"), ("company_id", "=", asset.company_id.id)],
            limit=1,
        )
        move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "journal_id": journal.id,
                "date": self.period_date,
                "ref": _("Depreciation: %s") % asset.name,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "account_id": asset.depreciation_expense_account_id.id,
                            "name": asset.name,
                            "debit": self.amount,
                            "credit": 0.0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "account_id": asset.accumulated_depreciation_account_id.id,
                            "name": asset.name,
                            "debit": 0.0,
                            "credit": self.amount,
                        },
                    ),
                ],
            }
        )
        move.action_post()
        self.write({"state": "posted", "move_id": move.id})
        if asset.accumulated_depreciation >= asset.acquisition_cost - asset.salvage_value:
            asset.state = "fully_depreciated"

    @api.model
    def _bpro_cron_post_due_depreciation(self):
        today = fields.Date.context_today(self)
        due_lines = self.search([("state", "=", "draft"), ("period_date", "<=", today)])
        for line in due_lines:
            line._bpro_post()
