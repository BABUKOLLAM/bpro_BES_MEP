from odoo import api, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def write(self, vals):
        result = super().write(vals)
        if "discount" in vals:
            self.order_id._bpro_sync_discount_approval()
        return result

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        if any("discount" in v for v in vals_list):
            lines.order_id._bpro_sync_discount_approval()
        return lines
