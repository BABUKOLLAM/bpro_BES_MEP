from odoo import api, fields, models


class BproQualityPoint(models.Model):
    _name = "bpro.quality.point"
    _description = "Quality Checkpoint Definition"

    name = fields.Char(required=True)
    operation = fields.Selection(
        [("incoming", "Incoming Receipt"), ("manufacturing", "Manufacturing")],
        required=True,
    )
    product_tmpl_id = fields.Many2one(
        "product.template",
        string="Product",
        help="Leave empty to apply to every product (optionally narrowed by "
        "Product Category instead), not just one.",
    )
    product_category_id = fields.Many2one(
        "product.category",
        string="Product Category",
        help="Leave empty together with Product to apply to every product.",
    )
    instructions = fields.Text()
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    active = fields.Boolean(default=True)
    test_parameter_ids = fields.One2many(
        "bpro.quality.test.parameter", "quality_point_id", string="Test Parameters",
        help="Measurable specs (e.g. Thickness, Tensile Strength) checked against "
        "min/max limits every time this checkpoint is used. Leave empty for a "
        "simple pass/fail checkpoint with no measured values.",
    )

    @api.model
    def _bpro_applicable_points(self, operation, product, company):
        points = self.search(
            [
                ("operation", "=", operation),
                ("company_id", "=", company.id),
            ]
        )
        return points.filtered(
            lambda p: (not p.product_tmpl_id or p.product_tmpl_id == product.product_tmpl_id)
            and (not p.product_category_id or p.product_category_id == product.categ_id)
        )
