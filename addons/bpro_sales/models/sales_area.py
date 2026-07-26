from odoo import fields, models


class BproSalesArea(models.Model):
    _name = "bpro.sales.area"
    _description = "Sales Area / Territory"
    _order = "name"

    name = fields.Char(required=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )

    _sql_constraints = [
        (
            "name_company_uniq",
            "unique(name, company_id)",
            "This sales area already exists for this company.",
        )
    ]
