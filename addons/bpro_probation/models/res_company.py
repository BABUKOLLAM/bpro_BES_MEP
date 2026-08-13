from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    probation_months = fields.Integer(
        string="Probation Period (Months)",
        default=6,
        help="Company policy, not statute - India has no statutory "
        "probation length for factory workers. Applied to new hires at "
        "Finalize Hiring; individual extensions are handled per "
        "employee, not here.",
    )
