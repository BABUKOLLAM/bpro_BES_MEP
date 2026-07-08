from datetime import timedelta

from odoo import api, fields, models


class BproSalesTarget(models.Model):
    _name = "bpro.sales.target"
    _description = "Sales Target vs Actual"
    _order = "date_from desc, user_id"

    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    user_id = fields.Many2one("res.users", string="Salesperson", required=True)
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    currency_id = fields.Many2one(related="company_id.currency_id")
    target_amount = fields.Monetary(required=True)
    # Not stored: this must reflect newly-confirmed sale.order records
    # live, and @api.depends can't track that external, non-relational
    # dependency, so a stored value would go stale until this record's own
    # fields were next edited.
    actual_amount = fields.Monetary(compute="_compute_actual_amount")
    attainment_pct = fields.Float(
        string="Attainment %", compute="_compute_actual_amount"
    )

    @api.depends("user_id", "company_id", "date_from", "date_to", "target_amount")
    def _compute_actual_amount(self):
        for target in self:
            if not (target.user_id and target.date_from and target.date_to):
                target.actual_amount = 0.0
                target.attainment_pct = 0.0
                continue
            orders = self.env["sale.order"].search(
                [
                    ("user_id", "=", target.user_id.id),
                    ("company_id", "=", target.company_id.id),
                    ("state", "=", "sale"),
                    ("date_order", ">=", target.date_from),
                    ("date_order", "<", target.date_to + timedelta(days=1)),
                ]
            )
            target.actual_amount = sum(orders.mapped("amount_total"))
            target.attainment_pct = (
                (target.actual_amount / target.target_amount * 100)
                if target.target_amount
                else 0.0
            )
