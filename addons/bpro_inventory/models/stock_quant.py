from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_is_zero


class StockQuant(models.Model):
    _name = "stock.quant"
    # stock.quant has neither mail.thread nor mail.activity.mixin natively,
    # unlike sale.order - bring them explicitly (bpro.approval.mixin itself
    # deliberately doesn't, to avoid an MRO conflict on models that do
    # already have them).
    _inherit = ["stock.quant", "mail.thread", "mail.activity.mixin", "bpro.approval.mixin"]

    bpro_adjustment_reason = fields.Char(
        string="Adjustment Reason",
        help="Required for any manual stock adjustment (FR-INV-005).",
    )

    def _approval_policy_key(self):
        return "stock_adjustment_value"

    def _approval_amount(self):
        self.ensure_one()
        return abs(self.inventory_diff_quantity) * (self.product_id.standard_price or 0.0)

    def _approval_group_xmlid(self):
        return "stock.group_stock_manager"

    def _bpro_has_diff(self):
        self.ensure_one()
        rounding = self.product_uom_id.rounding
        return not float_is_zero(self.inventory_diff_quantity, precision_rounding=rounding)

    def action_apply_inventory(self):
        blocked = self.env["stock.quant"]
        applicable = self.env["stock.quant"]
        for quant in self:
            if not quant._bpro_has_diff():
                applicable |= quant
                continue
            if not quant.bpro_adjustment_reason:
                raise UserError(
                    _(
                        "A reason is required for %s before this stock "
                        "adjustment can be applied."
                    )
                    % quant.product_id.display_name
                )
            if (
                quant._approval_threshold_exceeded()
                and quant.approval_state != "approved"
            ):
                if quant.approval_state != "pending":
                    quant.action_request_approval()
                blocked |= quant
            else:
                applicable |= quant

        result = None
        if applicable:
            result = super(StockQuant, applicable).action_apply_inventory()
            applicable.write({"approval_state": "none"})
        if blocked:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "warning",
                    "title": _("Approval required"),
                    "message": _(
                        "%d adjustment(s) exceed the configured value threshold "
                        "and were sent for manager approval instead of being applied."
                    )
                    % len(blocked),
                },
            }
        return result

    def action_approve(self):
        result = super().action_approve()
        self.action_apply_inventory()
        return result

    def action_reject(self, reason=None):
        result = super().action_reject(reason=reason)
        self.action_clear_inventory_quantity()
        return result

    def _get_inventory_move_values(
        self, qty, location_id, location_dest_id, package_id=False, package_dest_id=False
    ):
        vals = super()._get_inventory_move_values(
            qty,
            location_id,
            location_dest_id,
            package_id=package_id,
            package_dest_id=package_dest_id,
        )
        vals.update(
            {
                "bpro_adjustment_reason": self.bpro_adjustment_reason,
                "bpro_before_qty": self.quantity,
                "bpro_after_qty": self.inventory_quantity,
            }
        )
        return vals
