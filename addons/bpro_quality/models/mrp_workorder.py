from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MrpWorkorder(models.Model):
    _inherit = "mrp.workorder"

    bpro_quality_check_ids = fields.One2many(
        "bpro.quality.check", "workorder_id", string="Quality Checks"
    )

    @api.model_create_multi
    def create(self, vals_list):
        # Created as part of mrp.production.action_confirm() - a separate,
        # non-raising transaction that happens well before button_finish(),
        # so a check created here survives even if button_finish() later
        # raises in its own call (same proactive-write-vs-reactive-raise
        # lesson as bpro.approval.mixin - see stock_picking.py for the
        # equivalent on the receipt side).
        workorders = super().create(vals_list)
        workorders._bpro_create_pending_quality_checks()
        return workorders

    def _bpro_create_pending_quality_checks(self):
        Check = self.env["bpro.quality.check"]
        Point = self.env["bpro.quality.point"]
        for workorder in self:
            product = workorder.production_id.product_id
            if not product:
                continue
            points = Point._bpro_applicable_points(
                "manufacturing", product, workorder.company_id
            )
            existing_points = workorder.bpro_quality_check_ids.quality_point_id
            for point in points - existing_points:
                Check.create(
                    {
                        "quality_point_id": point.id,
                        "workorder_id": workorder.id,
                        "product_id": product.id,
                        "company_id": workorder.company_id.id,
                    }
                )

    def button_finish(self):
        # Read-only check: quality checks are created proactively at
        # workorder creation time (see create() above), so this never
        # writes before raising.
        workorders_to_end = self.filtered(lambda wo: wo.state not in ("done", "cancel"))
        blocked = workorders_to_end.filtered(
            lambda wo: wo.bpro_quality_check_ids.filtered(lambda c: c.result != "pass")
        )
        if blocked:
            raise UserError(
                _(
                    "%s has quality checks that are not yet passed. This "
                    "work order cannot be finished until every quality "
                    "check passes."
                )
                % ", ".join(blocked.mapped("display_name"))
            )
        return super().button_finish()
