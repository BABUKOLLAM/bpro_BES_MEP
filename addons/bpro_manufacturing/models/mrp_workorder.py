from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MrpWorkorder(models.Model):
    _inherit = "mrp.workorder"

    # FR-MFG-005: native Odoo has no cumulative rejected-quantity field on
    # the work order itself - rejects only exist as separate stock.scrap
    # records. This is a live compute (like bpro.sales.target.actual_amount
    # in bpro_sales) rather than store=True, since scrap totals depend on
    # stock.scrap records outside this model that @api.depends can't track.
    bpro_qty_rejected = fields.Float(
        string="Rejected Quantity",
        compute="_compute_bpro_qty_rejected",
        help="Sum of validated stock.scrap quantities recorded against this operation.",
    )
    bpro_reject_reason_id = fields.Many2one(
        "stock.scrap.reason.tag",
        string="Last Reject Reason",
        help="Informational: the reason used on the most recent reject capture. "
        "The authoritative per-event reason lives on each stock.scrap record.",
    )
    bpro_reject_qty_input = fields.Float(
        string="Qty to Reject Now",
        help="Enter a quantity and a reason above, then click 'Record Reject'.",
    )

    # FR-MFG-002: native manual reschedule (write() on date_start/
    # date_finished/workcenter_id) recomputes duration but doesn't flag an
    # overlap the way the automated Plan button's scheduler does. This is
    # a non-blocking warning, matching the FR's "display a warning if
    # capacity is exceeded" (not "block the save").
    bpro_capacity_warning = fields.Char(
        string="Capacity Warning", compute="_compute_bpro_capacity_warning"
    )

    # FR-MFG-009: qty_production (planned) and qty_produced (actual) are
    # both native fields on this same model, so - unlike the two computes
    # above - this dependency IS trackable via @api.depends and safe to
    # store for reporting/pivot performance.
    bpro_variance_qty = fields.Float(
        string="Output Variance (Qty)",
        compute="_compute_bpro_variance",
        store=True,
    )
    bpro_variance_pct = fields.Float(
        string="Output Variance (%)",
        compute="_compute_bpro_variance",
        store=True,
    )

    def _compute_bpro_qty_rejected(self):
        scrap_data = self.env["stock.scrap"]._read_group(
            [("workorder_id", "in", self.ids), ("state", "=", "done")],
            ["workorder_id"],
            ["scrap_qty:sum"],
        )
        totals = {workorder.id: qty_sum for workorder, qty_sum in scrap_data}
        for wo in self:
            wo.bpro_qty_rejected = totals.get(wo.id, 0.0)

    def _compute_bpro_capacity_warning(self):
        for wo in self:
            wo.bpro_capacity_warning = False
            if not (wo.workcenter_id and wo.date_start and wo.date_finished):
                continue
            overlapping = self.search(
                [
                    ("id", "!=", wo.id),
                    ("workcenter_id", "=", wo.workcenter_id.id),
                    ("state", "not in", ("done", "cancel")),
                    ("date_start", "<", wo.date_finished),
                    ("date_finished", ">", wo.date_start),
                ]
            )
            capacity = wo.workcenter_id._get_capacity(wo.product_id)
            booked = len(overlapping) + 1
            if booked > capacity:
                wo.bpro_capacity_warning = _(
                    "%(workcenter)s is booked beyond its capacity (%(capacity)s) for "
                    "this timeslot: %(count)s overlapping work order(s)."
                ) % {
                    "workcenter": wo.workcenter_id.name,
                    "capacity": capacity,
                    "count": booked,
                }

    @api.depends("qty_production", "qty_produced")
    def _compute_bpro_variance(self):
        for wo in self:
            wo.bpro_variance_qty = wo.qty_produced - wo.qty_production
            wo.bpro_variance_pct = (
                (wo.bpro_variance_qty / wo.qty_production * 100)
                if wo.qty_production
                else 0.0
            )

    def action_bpro_record_production(self, qty_completed=0.0, qty_rejected=0.0, reason_id=None):
        """Unified capture for FR-MFG-005: completed quantity and (if any)
        rejected quantity with a reason, in one call - native Odoo needs
        two separate actions (the Produce screen, then a standalone
        stock.scrap record with no reason prompt) to do the same thing."""
        self.ensure_one()
        if qty_completed:
            self.qty_producing = qty_completed
        if qty_rejected:
            if not reason_id:
                raise UserError(
                    _("A reason is required when recording a rejected quantity.")
                )
            scrap = self.env["stock.scrap"].create(
                {
                    "product_id": self.product_id.id,
                    "scrap_qty": qty_rejected,
                    "workorder_id": self.id,
                    "production_id": self.production_id.id,
                    "scrap_reason_tag_ids": [(6, 0, [reason_id])],
                }
            )
            # do_scrap() directly, not action_validate(): the latter's
            # check_available_qty() assumes scrapping *existing* on-hand
            # stock, but this qty is newly-produced WIP being rejected
            # before it's ever counted into finished-goods on-hand -
            # that check would (and did, before this fix) silently redirect
            # to an "insufficient quantity" wizard action instead of
            # completing, leaving the scrap stuck in draft.
            scrap.do_scrap()
            self.bpro_reject_reason_id = reason_id
        return True

    def action_bpro_record_reject_button(self):
        """UI entry point for action_bpro_record_production's reject path -
        reads the two input fields the form exposes, then clears the
        quantity input so the same field can be reused for the next
        reject event without carrying a stale value forward."""
        self.ensure_one()
        if self.bpro_reject_qty_input:
            self.action_bpro_record_production(
                qty_rejected=self.bpro_reject_qty_input,
                reason_id=self.bpro_reject_reason_id.id,
            )
            self.bpro_reject_qty_input = 0.0
        return True
