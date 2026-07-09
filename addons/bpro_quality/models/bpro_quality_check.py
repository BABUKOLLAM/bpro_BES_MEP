from odoo import _, api, fields, models
from odoo.exceptions import UserError


class BproQualityCheck(models.Model):
    _name = "bpro.quality.check"
    _description = "Quality Check"

    quality_point_id = fields.Many2one(
        "bpro.quality.point", required=True, ondelete="restrict"
    )
    picking_id = fields.Many2one("stock.picking", ondelete="cascade")
    workorder_id = fields.Many2one("mrp.workorder", ondelete="cascade")
    product_id = fields.Many2one("product.product", required=True)
    company_id = fields.Many2one("res.company", required=True)
    result = fields.Selection(
        [("none", "To Do"), ("pass", "Pass"), ("fail", "Fail")],
        default="none",
        required=True,
    )
    note = fields.Text()
    checked_by = fields.Many2one("res.users", readonly=True, copy=False)
    checked_at = fields.Datetime(readonly=True, copy=False)
    line_ids = fields.One2many(
        "bpro.quality.check.line", "check_id", string="Test Results"
    )
    nonconformance_ids = fields.One2many(
        "bpro.quality.nonconformance", "check_id", string="Non-Conformances"
    )

    @api.model_create_multi
    def create(self, vals_list):
        checks = super().create(vals_list)
        for check in checks:
            for parameter in check.quality_point_id.test_parameter_ids:
                self.env["bpro.quality.check.line"].create(
                    {"check_id": check.id, "parameter_id": parameter.id}
                )
        return checks

    def action_bpro_pass(self):
        out_of_spec = self.line_ids.filtered(lambda l: not l.is_within_spec)
        if out_of_spec:
            raise UserError(
                _(
                    "Cannot pass this check - %s is outside its spec limits. "
                    "Correct the measured value or fail the check instead."
                )
                % ", ".join(out_of_spec.mapped("parameter_id.name"))
            )
        for check in self:
            check.write(
                {
                    "result": "pass",
                    "checked_by": self.env.user.id,
                    "checked_at": fields.Datetime.now(),
                }
            )

    def action_bpro_fail(self):
        for check in self:
            check.write(
                {
                    "result": "fail",
                    "checked_by": self.env.user.id,
                    "checked_at": fields.Datetime.now(),
                }
            )
            if not check.nonconformance_ids:
                self.env["bpro.quality.nonconformance"].create(
                    {
                        "check_id": check.id,
                        "description": check.note or _("Quality check failed."),
                    }
                )

    def action_print_coa(self):
        return self.env.ref(
            "bpro_quality.action_report_bpro_quality_coa"
        ).report_action(self, config=False)
