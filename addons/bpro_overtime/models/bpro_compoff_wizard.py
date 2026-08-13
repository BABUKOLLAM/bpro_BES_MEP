from datetime import datetime, time

from pytz import timezone as pytz_timezone, UTC

from odoo import fields, models
from odoo.exceptions import UserError


class BproCompoffWizard(models.TransientModel):
    _name = "bpro.compoff.wizard"
    _description = "Convert Approved Overtime to Compensatory Off"

    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    summary = fields.Text(readonly=True)

    def action_convert(self):
        self.ensure_one()
        if self.env.company.ot_compensation != "compoff":
            raise UserError(
                "This company's overtime policy is 'Pay with Salary' - "
                "comp-off conversion would double-compensate the same hours."
            )
        if self.date_from > self.date_to:
            raise UserError("The start date must be on or before the end date.")
        compoff_type = self.env.ref("bpro_overtime.leave_type_compoff")
        Attendance = self.env["hr.attendance"].sudo()
        notes = []
        employees = self.env["hr.employee"].search(
            [("company_id", "=", self.env.company.id)]
        )
        for employee in employees:
            tz = pytz_timezone(employee.tz or "Asia/Kolkata")
            start = tz.localize(datetime.combine(self.date_from, time.min)).astimezone(UTC).replace(tzinfo=None)
            end = tz.localize(datetime.combine(self.date_to, time.max)).astimezone(UTC).replace(tzinfo=None)
            attendances = Attendance.search([
                ("employee_id", "=", employee.id),
                ("overtime_status", "=", "approved"),
                ("bpro_compoff_converted", "=", False),
                ("check_in", ">=", start),
                ("check_in", "<=", end),
            ])
            hours = sum(attendances.mapped("validated_overtime_hours"))
            # 8 OT hours = 1 day, floored to half-days - a 3-hour
            # remainder stays unconverted (its attendances stay
            # unflagged only if NO credit was given for them; since
            # credit is computed across the batch, flag them all and
            # credit the floored figure - the remainder policy choice
            # is documented here rather than hidden).
            days = int(hours / 4.0) / 2.0
            if not days:
                continue
            self.env["hr.leave.allocation"].sudo().create({
                "name": f"Comp-off for OT {self.date_from} - {self.date_to}",
                "employee_id": employee.id,
                "holiday_status_id": compoff_type.id,
                "number_of_days": days,
                "state": "confirm",
                "date_from": self.date_from,
            }).action_approve()
            attendances.write({"bpro_compoff_converted": True})
            notes.append(f"{employee.name}: {hours:.1f} OT hour(s) -> {days} day(s)")
        self.summary = "\n".join(notes) if notes else "No unconverted approved overtime found."
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    bpro_compoff_converted = fields.Boolean(
        default=False, copy=False,
        help="Set once this attendance's approved overtime has been "
        "converted to Compensatory Off - the guard that makes re-running "
        "the conversion wizard safe (never double-credits).",
    )
