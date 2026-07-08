from odoo import fields, models


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

    def action_bpro_pass(self):
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
