from odoo import _, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = ["sale.order", "bpro.approval.mixin"]

    def _approval_policy_key(self):
        return "sales_discount_pct"

    def _approval_amount(self):
        self.ensure_one()
        discounts = self.order_line.filtered(lambda l: not l.display_type).mapped(
            "discount"
        )
        return max(discounts) if discounts else 0.0

    def _approval_group_xmlid(self):
        return "sales_team.group_sale_manager"

    def _bpro_sync_discount_approval(self):
        """Called from sale_order_line.py whenever a line discount is
        saved. Re-evaluates the approval gate as part of that normal save
        - a previously-decided order is reset, and any order now over
        threshold gets a fresh approval request - so action_confirm and
        action_quotation_send only ever need to read approval_state, never
        write to it (see the docstring on action_request_approval)."""
        self.filtered(
            lambda o: o.approval_state in ("approved", "rejected")
        ).write({"approval_state": "none"})
        self.filtered(
            lambda o: o.approval_state == "none" and o._approval_threshold_exceeded()
        ).action_request_approval()

    def action_quotation_send(self):
        # Read-only check: the approval request itself is raised
        # proactively when the discount is saved (sale_order_line.py), not
        # here - raising UserError rolls back the whole transaction, which
        # would discard a request-approval write made in this same call.
        for order in self:
            if (
                order._approval_threshold_exceeded()
                and order.approval_state != "approved"
            ):
                raise UserError(
                    _(
                        "This quotation's discount exceeds the approval threshold "
                        "and is pending manager approval. It can be sent once "
                        "approved."
                    )
                )
        return super().action_quotation_send()

    def _confirmation_error_message(self):
        error = super()._confirmation_error_message()
        if error:
            return error
        # FR-SAL-010, credit half: native Odoo only computes a non-blocking
        # partner_credit_warning; reuse its message but actually enforce it.
        if self.partner_credit_warning:
            return self.partner_credit_warning
        # FR-SAL-010, stock half: native Odoo allows confirming an order it
        # can't currently fulfil and backorders it instead - block here.
        stock_error = self._bpro_stock_shortage_message()
        if stock_error:
            return stock_error
        # FR-SAL-008: same discount gate as action_quotation_send, so a rep
        # can't bypass approval by skipping "Send" and confirming directly.
        # Read-only, same reasoning as action_quotation_send above.
        if (
            self._approval_threshold_exceeded()
            and self.approval_state != "approved"
        ):
            return _(
                "This order's discount exceeds the approval threshold and is "
                "pending manager approval. It can be confirmed once approved."
            )
        return False

    def _bpro_stock_shortage_message(self):
        self.ensure_one()
        shortages = []
        for line in self.order_line:
            product = line.product_id
            if line.display_type or not product or not product.is_storable:
                continue
            free_qty = product.with_context(warehouse=self.warehouse_id.id).free_qty
            if line.product_uom_qty > free_qty:
                shortages.append(
                    _("%(product)s: ordered %(ordered)s, only %(available)s available")
                    % {
                        "product": product.display_name,
                        "ordered": line.product_uom_qty,
                        "available": free_qty,
                    }
                )
        if not shortages:
            return False
        return _("Insufficient stock to confirm this order:\n%s") % "\n".join(
            shortages
        )
