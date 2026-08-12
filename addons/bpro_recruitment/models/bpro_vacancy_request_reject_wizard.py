from odoo import fields, models


class BproVacancyRequestRejectWizard(models.TransientModel):
    _name = "bpro.vacancy.request.reject.wizard"
    _description = "Reject Vacancy Request"

    request_id = fields.Many2one("bpro.vacancy.request", required=True)
    reason = fields.Text(required=True)

    def action_confirm_reject(self):
        self.ensure_one()
        self.request_id.action_reject()
        self.request_id.rejection_reason = self.reason
