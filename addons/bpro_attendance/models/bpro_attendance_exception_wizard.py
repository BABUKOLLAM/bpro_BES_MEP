from odoo import fields, models
from odoo.exceptions import UserError


class BproAttendanceExceptionWizard(models.TransientModel):
    _name = "bpro.attendance.exception.wizard"
    _description = "Detect Attendance Exceptions"

    date_from = fields.Date(required=True, default=lambda self: fields.Date.context_today(self))
    date_to = fields.Date(required=True, default=lambda self: fields.Date.context_today(self))

    def action_detect(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError("The start date must be on or before the end date.")
        created = self.env["bpro.attendance.exception"]._detect_exceptions(self.date_from, self.date_to)
        return {
            "type": "ir.actions.act_window",
            "name": "Attendance Exceptions",
            "res_model": "bpro.attendance.exception",
            "view_mode": "list,form",
            "domain": [("id", "in", created.ids)],
            "context": {"search_default_pending": 1},
        }
