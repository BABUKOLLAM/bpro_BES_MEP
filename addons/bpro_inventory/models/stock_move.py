from odoo import fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    # Durable audit trail for FR-INV-006: the native stock.move record
    # already carries who (create_uid) and when (create_date); these three
    # fields add the reason code and the before/after quantities that
    # weren't otherwise recoverable once the quant's count-mode fields
    # reset after applying.
    bpro_adjustment_reason = fields.Char(string="Adjustment Reason")
    bpro_before_qty = fields.Float(string="Qty Before Adjustment")
    bpro_after_qty = fields.Float(string="Qty After Adjustment")
