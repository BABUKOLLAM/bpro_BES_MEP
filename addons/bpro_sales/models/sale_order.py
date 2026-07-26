from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

RECURRENCE_INTERVALS = {
    "monthly": relativedelta(months=1),
    "quarterly": relativedelta(months=3),
    "yearly": relativedelta(years=1),
}


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = ["sale.order", "bpro.approval.mixin"]

    # Commission (Should/Could FR): frozen at confirmation time, not a
    # live compute - a later change to the salesperson's rate must not
    # retroactively alter a commission already earned on a past order.
    bpro_commission_pct = fields.Float(string="Commission %", readonly=True, copy=False)
    bpro_commission_amount = fields.Monetary(
        string="Commission Amount", readonly=True, copy=False
    )

    # Recurring orders (Should/Could FR): only the "master" order carries
    # the recurrence config and keeps bpro_is_recurring True across
    # renewals; each generated child is a one-off copy linked back via
    # bpro_recurring_parent_id, not itself recurring, keeping exactly one
    # active "next due date" per subscription.
    bpro_is_recurring = fields.Boolean(string="Recurring Order", copy=False)
    bpro_recurrence_interval = fields.Selection(
        [
            ("monthly", "Monthly"),
            ("quarterly", "Quarterly"),
            ("yearly", "Yearly"),
        ],
        string="Recurs Every",
    )
    bpro_next_recurrence_date = fields.Date(string="Next Renewal Date", copy=False)
    bpro_recurring_parent_id = fields.Many2one(
        "sale.order",
        string="Recurring From",
        readonly=True,
        copy=False,
        help="The master recurring order this one was auto-generated from.",
    )

    sales_area_id = fields.Many2one(
        "bpro.sales.area",
        string="Sales Area",
        help="Delivery district/territory this order belongs to, for area-wise sales reporting.",
    )

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

    def _action_confirm(self):
        res = super()._action_confirm()
        for order in self:
            rate = self.env["bpro.commission.rate"].get_rate(
                order.company_id, order.user_id
            )
            order.bpro_commission_pct = rate
            order.bpro_commission_amount = order.amount_untaxed * rate / 100.0
            if order.bpro_is_recurring and not order.bpro_next_recurrence_date:
                order.bpro_next_recurrence_date = order._bpro_next_date(
                    fields.Date.context_today(order)
                )
        return res

    def _bpro_next_date(self, from_date):
        interval = RECURRENCE_INTERVALS.get(self.bpro_recurrence_interval)
        return from_date + interval if interval else from_date

    @api.model
    def _bpro_cron_generate_recurring_orders(self):
        """Daily cron: renew every master order whose next renewal date
        has arrived. The generated child is a one-off copy (not itself
        recurring, linked back via bpro_recurring_parent_id); the master
        keeps recurring and has its own due date advanced, so re-running
        the cron the same day is a no-op for orders already renewed.

        FOR UPDATE SKIP LOCKED (not a plain search()) so an overlapping
        cron run can't select the same due master before either commits
        and generate two renewal orders for it - the search-then-write of
        bpro_next_recurrence_date below is otherwise a classic TOCTOU gap.
        """
        today = fields.Date.context_today(self)
        # raw SQL reads the table directly, bypassing the ORM cache - any
        # pending write still sitting in cache (e.g. this same method's own
        # bpro_next_recurrence_date advance from an earlier iteration) must
        # be flushed first or this query won't see it.
        self.env.flush_all()
        self.env.cr.execute(
            """
            SELECT id FROM sale_order
            WHERE bpro_is_recurring = true
              AND bpro_next_recurrence_date <= %s
              AND state = 'sale'
            FOR UPDATE SKIP LOCKED
            """,
            (today,),
        )
        masters = self.browse(row[0] for row in self.env.cr.fetchall())
        for master in masters:
            child = master.copy(
                {
                    "bpro_is_recurring": False,
                    "bpro_recurrence_interval": False,
                    "bpro_next_recurrence_date": False,
                    "bpro_recurring_parent_id": master.id,
                }
            )
            child.action_confirm()
            master.bpro_next_recurrence_date = master._bpro_next_date(
                master.bpro_next_recurrence_date
            )
