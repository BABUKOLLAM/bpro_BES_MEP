from odoo import fields, models


class BproQualityTestParameter(models.Model):
    _name = "bpro.quality.test.parameter"
    _description = "Quality Test Parameter"
    _order = "sequence, id"

    name = fields.Char(required=True, help="e.g. Thickness, Tensile Strength, Moisture Content")
    sequence = fields.Integer(default=10)
    quality_point_id = fields.Many2one(
        "bpro.quality.point", required=True, ondelete="cascade"
    )
    uom_name = fields.Char(string="Unit", help="e.g. mm, %, N/mm2")
    min_value = fields.Float(string="Min")
    max_value = fields.Float(string="Max")
    target_value = fields.Float(string="Target")
