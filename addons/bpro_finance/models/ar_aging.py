from collections import defaultdict

from odoo import api, fields, models

BUCKETS = ("current", "d1_30", "d31_60", "d61_90", "d90_plus")


class BproArAgingWizard(models.TransientModel):
    _name = "bpro.ar.aging.wizard"
    _inherit = ["bpro.xlsx.export.mixin"]
    _description = "AR Aging Report"

    _xlsx_line_model = "bpro.ar.aging.line"
    _xlsx_export_fields = [
        "partner_id", "current", "d1_30", "d31_60", "d61_90", "d90_plus", "total",
    ]

    as_of_date = fields.Date(default=fields.Date.context_today, required=True)
    line_ids = fields.One2many("bpro.ar.aging.line", "wizard_id", readonly=True)
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id
    )

    def action_generate(self):
        self.ensure_one()
        self.line_ids.unlink()
        data = self._get_aging_data(self.env.company, self.as_of_date)
        self.line_ids = [(0, 0, vals) for vals in data]
        return {
            "type": "ir.actions.act_window",
            "res_model": "bpro.ar.aging.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.model
    def _get_aging_data(self, company, as_of_date):
        """Returns a list of per-partner bucket dicts. A plain @api.model
        method (not tied to a saved wizard record) so it's directly unit
        testable without creating/saving a wizard."""
        move_lines = self.env["account.move.line"].search(
            [
                ("company_id", "=", company.id),
                ("account_id.account_type", "=", "asset_receivable"),
                ("parent_state", "=", "posted"),
                ("reconciled", "=", False),
            ]
        )
        buckets_by_partner = defaultdict(lambda: dict.fromkeys(BUCKETS, 0.0))
        for line in move_lines:
            residual = line.amount_residual
            if not residual:
                continue
            due_date = line.date_maturity or line.date
            days_overdue = (as_of_date - due_date).days
            buckets_by_partner[line.partner_id][self._bucket_for_days(days_overdue)] += (
                residual
            )
        return [
            {
                "partner_id": partner.id,
                **bucket_vals,
                "total": sum(bucket_vals.values()),
            }
            for partner, bucket_vals in buckets_by_partner.items()
        ]

    @staticmethod
    def _bucket_for_days(days):
        if days <= 0:
            return "current"
        if days <= 30:
            return "d1_30"
        if days <= 60:
            return "d31_60"
        if days <= 90:
            return "d61_90"
        return "d90_plus"


class BproArAgingLine(models.TransientModel):
    _name = "bpro.ar.aging.line"
    _description = "AR Aging Report Line"

    wizard_id = fields.Many2one("bpro.ar.aging.wizard", required=True, ondelete="cascade")
    partner_id = fields.Many2one("res.partner", string="Customer", required=True)
    currency_id = fields.Many2one(related="wizard_id.currency_id")
    current = fields.Monetary(string="Current")
    d1_30 = fields.Monetary(string="1-30 Days")
    d31_60 = fields.Monetary(string="31-60 Days")
    d61_90 = fields.Monetary(string="61-90 Days")
    d90_plus = fields.Monetary(string="90+ Days")
    total = fields.Monetary(string="Total")
