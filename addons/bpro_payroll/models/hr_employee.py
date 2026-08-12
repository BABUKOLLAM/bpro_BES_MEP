from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    pan = fields.Char(
        string="PAN",
        help="Permanent Account Number - shown on Form 16. Not validated "
        "for format here.",
    )
