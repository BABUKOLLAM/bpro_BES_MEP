from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    uan = fields.Char(
        string="UAN",
        groups="hr.group_hr_user",
        help="EPFO Universal Account Number - required on the ECR file. "
        "An employee without one is excluded from the ECR and reported "
        "in the filing wizard's summary.",
    )
    esi_number = fields.Char(
        string="ESI Number (IP)",
        groups="hr.group_hr_user",
        help="ESIC Insured Person number - required on the monthly "
        "contribution file for ESI-covered employees.",
    )
