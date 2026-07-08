from odoo import _, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    bpro_quality_check_ids = fields.One2many(
        "bpro.quality.check", "picking_id", string="Quality Checks"
    )

    def _bpro_create_pending_quality_checks(self):
        # Called from stock.move._action_confirm() (see stock_move.py), a
        # separate, non-raising transaction that happens well before
        # button_validate() (typically as part of confirming the source
        # purchase order) - never from _pre_action_done_hook itself, since a
        # check created in the SAME call as the eventual raise below would
        # be discarded when that raise rolls back the transaction (the same
        # proactive-write-vs-reactive-raise lesson as bpro.approval.mixin).
        Check = self.env["bpro.quality.check"]
        Point = self.env["bpro.quality.point"]
        for picking in self.filtered(lambda p: p.picking_type_id.code == "incoming"):
            for move in picking.move_ids.filtered(
                lambda m: m.product_id and m.state != "cancel"
            ):
                points = Point._bpro_applicable_points(
                    "incoming", move.product_id, picking.company_id
                )
                existing_points = picking.bpro_quality_check_ids.filtered(
                    lambda c: c.product_id == move.product_id
                ).quality_point_id
                for point in points - existing_points:
                    Check.create(
                        {
                            "quality_point_id": point.id,
                            "picking_id": picking.id,
                            "product_id": move.product_id.id,
                            "company_id": picking.company_id.id,
                        }
                    )

    def _pre_action_done_hook(self):
        # Read-only check: quality checks are created proactively (see
        # above), so this never writes before raising.
        blocked = self.filtered(
            lambda p: p.bpro_quality_check_ids.filtered(lambda c: c.result != "pass")
        )
        if blocked:
            raise UserError(
                _(
                    "%s has quality checks that are not yet passed. This "
                    "receipt cannot be validated until every quality check "
                    "passes."
                )
                % ", ".join(blocked.mapped("name"))
            )
        return super()._pre_action_done_hook()
