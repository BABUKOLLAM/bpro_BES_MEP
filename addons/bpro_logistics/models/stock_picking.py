from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    # purchase.report's own "Days to Receive" metric is date_planned minus
    # date_order - the PROMISED lead time, not an actual-arrival comparison.
    # There is no native check of whether a receipt actually showed up when
    # promised. bpro_promised_date/_delay_days/_on_time close that gap.
    bpro_promised_date = fields.Datetime(
        compute="_compute_bpro_vendor_performance", store=True
    )
    bpro_delay_days = fields.Float(
        compute="_compute_bpro_vendor_performance", store=True,
        help="Actual arrival minus promised date, in days. Negative or zero means on time.",
    )
    bpro_on_time = fields.Boolean(
        compute="_compute_bpro_vendor_performance", store=True
    )

    @api.depends("state", "date_done", "purchase_id.date_planned")
    def _compute_bpro_vendor_performance(self):
        for picking in self:
            promised = picking.purchase_id.date_planned
            if picking.state == "done" and picking.date_done and promised:
                picking.bpro_promised_date = promised
                picking.bpro_delay_days = (
                    picking.date_done - promised
                ).total_seconds() / 86400.0
                picking.bpro_on_time = picking.date_done <= promised
            else:
                picking.bpro_promised_date = False
                picking.bpro_delay_days = 0.0
                picking.bpro_on_time = False
