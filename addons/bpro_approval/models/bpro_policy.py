from odoo import api, fields, models


class BproPolicy(models.Model):
    _name = "bpro.policy"
    _description = "Configurable Approval Threshold"
    _rec_name = "key"
    _order = "company_id, key"

    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    key = fields.Char(
        required=True,
        help="Machine key looked up by an addon's approval mixin, "
        "e.g. 'sales_discount_pct' or 'stock_adjustment_value'.",
    )
    numeric_value = fields.Float(required=True)
    description = fields.Char()

    _sql_constraints = [
        (
            "company_key_unique",
            "UNIQUE(company_id, key)",
            "Only one value may be set per policy key per company.",
        ),
    ]

    @api.model
    def get_value(self, company, key, default=0.0):
        """Return the configured threshold for (company, key), or default
        if the client hasn't set one yet. Runs as sudo: this is looked up
        internally by approval-mixin logic for any user role (sales rep,
        stock user, ...), not just the Super Admins who may edit policies.
        """
        policy = self.sudo().search(
            [("company_id", "=", company.id), ("key", "=", key)], limit=1
        )
        return policy.numeric_value if policy else default
