from odoo import fields, models


class BproItemTarget(models.Model):
    _name = "bpro.item.target"
    _description = "Per-Product Production/Sales Target"
    _order = "product_id"

    product_id = fields.Many2one("product.product", required=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    monthly_production_qty_target = fields.Float(
        string="Monthly Production Target (Qty)",
        help="Compared against actual quantity produced this month, in the Executive Dashboard's item-wise production table.",
    )
    weekly_sales_qty_target = fields.Float(
        string="Weekly Sales Target (Qty)",
        help="Compared against actual quantity sold this week, in the Executive Dashboard's item-wise sales table.",
    )

    _sql_constraints = [
        (
            "product_company_uniq",
            "unique(product_id, company_id)",
            "This product already has a target configured for this company.",
        )
    ]
