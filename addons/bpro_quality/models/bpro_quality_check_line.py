from odoo import api, fields, models


class BproQualityCheckLine(models.Model):
    _name = "bpro.quality.check.line"
    _description = "Quality Check Test Result"
    _order = "sequence, id"

    check_id = fields.Many2one(
        "bpro.quality.check", required=True, ondelete="cascade"
    )
    sequence = fields.Integer(default=10)
    parameter_id = fields.Many2one(
        "bpro.quality.test.parameter", required=True, ondelete="restrict"
    )
    uom_name = fields.Char(related="parameter_id.uom_name", string="Unit")
    min_value = fields.Float(related="parameter_id.min_value")
    max_value = fields.Float(related="parameter_id.max_value")
    measured_value = fields.Float()
    is_within_spec = fields.Boolean(compute="_compute_is_within_spec", store=True)

    @api.depends("measured_value", "parameter_id.min_value", "parameter_id.max_value")
    def _compute_is_within_spec(self):
        for line in self:
            line.is_within_spec = (
                line.parameter_id.min_value <= line.measured_value <= line.parameter_id.max_value
            )
