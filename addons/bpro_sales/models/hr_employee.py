from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    bpro_sales_area_ids = fields.Many2many(
        "bpro.sales.area",
        string="Coverage Areas",
        help="Districts/regions this employee covers - field sales & marketing staff only.",
    )
