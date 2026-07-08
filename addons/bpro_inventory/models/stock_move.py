from odoo import _, api, fields, models
from odoo.exceptions import UserError


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

    # FR-INV-003/004: barcode scanning to confirm receipt/pick against the
    # expected SKU/lot. stock_barcode (the native scanning app) is
    # Enterprise-only and unavailable in this Community image - this is
    # the planned fallback, a validated text field a keyboard-wedge
    # scanner (or manual typing) can fill. Left empty, a line behaves
    # exactly as it always did - scanning is optional, not a new mandatory
    # step, since real scanner hardware is an explicitly deferred NFR.
    # Whatever IS entered must match, immediately (onchange, for the
    # native "reject the scan and display an error" UX) and again at
    # write() time (defense in depth against non-UI callers).
    bpro_scanned_code = fields.Char(string="Scanned Barcode/Lot")

    def _bpro_valid_scan_codes(self):
        self.ensure_one()
        product = self.product_id
        codes = {code for code in (product.barcode, product.default_code) if code}
        for line in self.move_line_ids:
            if line.lot_id:
                codes.add(line.lot_id.name)
            if line.lot_name:
                codes.add(line.lot_name)
        return codes

    def _bpro_check_scanned_code(self):
        for move in self:
            if not move.bpro_scanned_code:
                continue
            if move.bpro_scanned_code not in move._bpro_valid_scan_codes():
                raise UserError(
                    _(
                        "Scanned code '%(code)s' does not match %(product)s "
                        "on this line - check the SKU/lot and rescan."
                    )
                    % {"code": move.bpro_scanned_code, "product": move.product_id.display_name}
                )

    @api.onchange("bpro_scanned_code")
    def _onchange_bpro_scanned_code(self):
        self._bpro_check_scanned_code()

    def write(self, vals):
        res = super().write(vals)
        if "bpro_scanned_code" in vals:
            self._bpro_check_scanned_code()
        return res
