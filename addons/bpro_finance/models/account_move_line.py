from odoo import api, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def write(self, vals):
        result = super().write(vals)
        if {"quantity", "price_unit"} & vals.keys():
            self.move_id._bpro_sync_match_approval()
        return result

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        if any({"quantity", "price_unit"} & v.keys() for v in vals_list):
            lines.move_id._bpro_sync_match_approval()
        return lines
