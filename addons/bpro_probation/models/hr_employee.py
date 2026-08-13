from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    # Default 'confirmed', NOT 'probation': employees created outside
    # the recruitment flow (go-live data import of the existing
    # workforce) must not all land back on probation. Only Finalize
    # Hiring explicitly puts a new hire into probation.
    probation_state = fields.Selection(
        [("probation", "On Probation"), ("confirmed", "Confirmed")],
        default="confirmed",
        required=True,
        tracking=True,
        groups="hr.group_hr_user",
    )
    probation_end_date = fields.Date(tracking=True, groups="hr.group_hr_user")
    confirmation_date = fields.Date(readonly=True, copy=False, groups="hr.group_hr_user")

    def action_confirm_probation(self):
        for employee in self:
            if employee.probation_state != "probation":
                raise UserError(f"{employee.name} is not on probation.")
        self.write({
            "probation_state": "confirmed",
            "confirmation_date": fields.Date.context_today(self),
        })

    def action_extend_probation(self, months=3):
        """Extension is a date move + chatter trail, not a third state -
        'on probation until <new date>' already says everything an
        extension needs to say."""
        for employee in self:
            if employee.probation_state != "probation":
                raise UserError(f"{employee.name} is not on probation.")
            base = employee.probation_end_date or fields.Date.context_today(employee)
            new_end = base + relativedelta(months=months)
            employee.probation_end_date = new_end
            employee.message_post(
                body=f"Probation extended by {months} month(s), now ending {new_end}."
            )

    @api.model
    def _cron_probation_due_reminders(self):
        due = self.search([
            ("probation_state", "=", "probation"),
            ("probation_end_date", "!=", False),
            ("probation_end_date", "<=", fields.Date.context_today(self)),
        ])
        for employee in due:
            employee.message_post(
                body="Probation period has ended - a confirmation or "
                "extension decision is due.",
            )
        return True
