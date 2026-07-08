from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "bpro.approval.mixin"]

    bpro_match_mismatch = fields.Text(compute="_compute_bpro_match_mismatch")

    def _approval_policy_key(self):
        return "three_way_match_tolerance_pct"

    def _approval_amount(self):
        self.ensure_one()
        return self._bpro_match_variance_pct()

    def _approval_group_xmlid(self):
        return "account.group_account_manager"

    def _bpro_match_lines(self):
        """(bill_line, po_line, qty_variance_pct, price_variance_pct) for
        every bill line linked to a purchase order line."""
        self.ensure_one()
        results = []
        for line in self.invoice_line_ids:
            po_line = line.purchase_line_id
            if not po_line:
                continue
            qty_variance = self._bpro_pct_diff(line.quantity, po_line.qty_received)
            price_variance = self._bpro_pct_diff(line.price_unit, po_line.price_unit)
            results.append((line, po_line, qty_variance, price_variance))
        return results

    @staticmethod
    def _bpro_pct_diff(actual, expected):
        if not expected:
            return 0.0 if not actual else 100.0
        return abs(actual - expected) / abs(expected) * 100.0

    def _bpro_match_variance_pct(self):
        self.ensure_one()
        matches = self._bpro_match_lines()
        if not matches:
            return 0.0
        return max(max(qty_var, price_var) for _l, _po, qty_var, price_var in matches)

    @api.depends(
        "invoice_line_ids.quantity",
        "invoice_line_ids.price_unit",
        "invoice_line_ids.purchase_line_id",
    )
    def _compute_bpro_match_mismatch(self):
        for move in self:
            details = []
            for bill_line, po_line, qty_var, price_var in move._bpro_match_lines():
                if qty_var or price_var:
                    details.append(
                        _(
                            "%(product)s: PO qty %(po_qty)s, received %(received)s, "
                            "billed %(billed)s at %(billed_price)s (PO price %(po_price)s)"
                        )
                        % {
                            "product": bill_line.product_id.display_name,
                            "po_qty": po_line.product_qty,
                            "received": po_line.qty_received,
                            "billed": bill_line.quantity,
                            "billed_price": bill_line.price_unit,
                            "po_price": po_line.price_unit,
                        }
                    )
            move.bpro_match_mismatch = "\n".join(details) if details else False

    def _bpro_sync_match_approval(self):
        """Called from account_move_line.py whenever a bill line's qty or
        price is saved - see bpro.approval.mixin.action_request_approval's
        docstring for why this must happen proactively at save time, not
        reactively inside action_post's block."""
        bills = self.filtered(lambda m: m.move_type == "in_invoice")
        bills.filtered(lambda m: m.approval_state in ("approved", "rejected")).write(
            {"approval_state": "none"}
        )
        bills.filtered(
            lambda m: m.approval_state == "none" and m._approval_threshold_exceeded()
        ).action_request_approval()

    def action_post(self):
        for move in self:
            if (
                move.move_type == "in_invoice"
                and move._bpro_match_lines()
                and move._approval_threshold_exceeded()
                and move.approval_state != "approved"
            ):
                raise UserError(
                    _(
                        "This bill's quantity/price varies from the purchase order "
                        "beyond the configured tolerance and is pending manager "
                        "approval:\n%s"
                    )
                    % (move.bpro_match_mismatch or "")
                )
        return super().action_post()
