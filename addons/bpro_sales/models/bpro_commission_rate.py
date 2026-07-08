from odoo import api, fields, models


class BproCommissionRate(models.Model):
    _name = "bpro.commission.rate"
    _description = "Per-Salesperson Commission Rate"
    _rec_name = "user_id"

    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    user_id = fields.Many2one("res.users", required=True, string="Salesperson")
    commission_pct = fields.Float(
        required=True,
        string="Commission %",
        help="Overrides the company-wide default_commission_pct bpro.policy "
        "value for this salesperson.",
    )

    _sql_constraints = [
        (
            "user_company_unique",
            "UNIQUE(user_id, company_id)",
            "Only one commission rate may be set per salesperson per company.",
        ),
    ]

    @api.model
    def get_rate(self, company, user):
        """Per-salesperson override if one exists, else the company-wide
        default_commission_pct bpro.policy value, else 0.0."""
        rate = self.sudo().search(
            [("company_id", "=", company.id), ("user_id", "=", user.id)], limit=1
        )
        if rate:
            return rate.commission_pct
        return self.env["bpro.policy"].get_value(
            company, "default_commission_pct", default=0.0
        )
