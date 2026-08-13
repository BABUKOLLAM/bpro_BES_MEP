from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    exit_notice_days = fields.Integer(
        string="Exit Notice Period (Days)",
        default=30,
        help="Default notice period prefilled on a new resignation. "
        "HR can shorten or waive it on each individual exit request - "
        "this is the company policy default, not a hard rule.",
    )
    gratuity_cap = fields.Float(
        string="Gratuity Statutory Cap",
        default=2000000.0,
        help="Payment of Gratuity Act ceiling (Rs 20,00,000 since the "
        "2018 amendment). Kept configurable because the cap is revised "
        "by notification from time to time - update here, no code "
        "change needed.",
    )
