from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    department_id = fields.Many2one(
        "hr.department",
        string="Ordering Department",
        index=True,
        help="Set automatically when the RFQ originates from a department "
        "order; can also be set manually for department-wise reporting.",
    )
