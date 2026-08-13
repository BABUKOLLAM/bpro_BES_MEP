from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    ot_compensation = fields.Selection(
        [("pay", "Pay with Salary"), ("compoff", "Compensatory Off")],
        default="pay",
        required=True,
        string="Overtime Compensation",
        help="Policy choice: approved overtime is either paid on the "
        "payslip (at the multiplier below) or converted to Compensatory "
        "Off leave via the conversion wizard - never both.",
    )
    ot_multiplier = fields.Float(
        default=2.0,
        string="OT Rate Multiplier",
        help="Factories Act 1948 s59 mandates twice the ordinary rate "
        "of wages for factory workers - keep 2.0 unless a different "
        "category of establishment applies.",
    )
