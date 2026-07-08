from odoo import api, models


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines.mapped("task_id")._bpro_sync_budget_approval()
        return lines

    def write(self, vals):
        tasks_before = self.mapped("task_id")
        res = super().write(vals)
        (tasks_before | self.mapped("task_id"))._bpro_sync_budget_approval()
        return res

    def unlink(self):
        tasks = self.mapped("task_id")
        res = super().unlink()
        tasks._bpro_sync_budget_approval()
        return res
