from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _action_confirm(self, merge=True, merge_into=False):
        pickings = self.picking_id
        res = super()._action_confirm(merge=merge, merge_into=merge_into)
        pickings.filtered(
            lambda p: p.picking_type_id.code == "incoming"
        )._bpro_create_pending_quality_checks()
        return res
