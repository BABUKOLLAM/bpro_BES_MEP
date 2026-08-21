from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    department_id = fields.Many2one(
        "hr.department",
        string="Ordering Department",
        index=True,
        help="Set automatically on issues created from a department order.",
    )
