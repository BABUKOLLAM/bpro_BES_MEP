from odoo import fields, models


class BillingPlan(models.Model):
    _name = "bpro.billing.plan"
    _description = "Subscription Plan"
    _order = "price_per_seat"

    name = fields.Char(string="Plan", required=True)
    price_per_seat = fields.Float(string="Price per Seat", required=True)
    period = fields.Selection(
        [("monthly", "Monthly"), ("yearly", "Yearly")],
        default="monthly",
        required=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    description = fields.Text(string="Includes")
    active = fields.Boolean(default=True)
