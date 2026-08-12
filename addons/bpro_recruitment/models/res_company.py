from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    joining_report_sla = fields.Selection(
        [
            ("2", "2 Days"),
            ("7", "1 Week"),
            ("15", "15 Days"),
            ("30", "1 Month"),
        ],
        default="7",
        required=True,
        help="How long a new joiner has to submit their joining report "
        "after their expected joining date - as per the requirement, "
        "this is a management/HR policy choice, not a fixed rule.",
    )
