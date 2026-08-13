from datetime import datetime, time, timedelta

from pytz import timezone as pytz_timezone, UTC

from odoo import api, fields, models
from odoo.exceptions import UserError


class BproAttendanceException(models.Model):
    _name = "bpro.attendance.exception"
    _description = "Attendance Exception (unexplained absence)"
    _order = "date desc"

    employee_id = fields.Many2one("hr.employee", required=True, ondelete="cascade")
    department_id = fields.Many2one(related="employee_id.department_id", store=True)
    date = fields.Date(required=True)
    state = fields.Selection(
        [
            ("pending", "Pending Review"),
            ("excused", "Excused"),
            ("confirmed_absent", "Confirmed Absent"),
        ],
        default="pending",
        required=True,
    )
    note = fields.Text()
    resolved_by = fields.Many2one("res.users", readonly=True, copy=False)
    resolved_date = fields.Datetime(readonly=True, copy=False)

    _sql_constraints = [
        (
            "employee_date_uniq",
            "unique(employee_id, date)",
            "An attendance exception for this employee and date already exists.",
        ),
    ]

    def action_excuse(self):
        for rec in self:
            if rec.state != "pending":
                raise UserError("Only a pending exception can be excused.")
        self.write({
            "state": "excused",
            "resolved_by": self.env.user.id,
            "resolved_date": fields.Datetime.now(),
        })

    def action_confirm_absent(self):
        for rec in self:
            if rec.state != "pending":
                raise UserError("Only a pending exception can be confirmed as absent.")
        self.write({
            "state": "confirmed_absent",
            "resolved_by": self.env.user.id,
            "resolved_date": fields.Datetime.now(),
        })

    def action_reset_pending(self):
        for rec in self:
            if rec.state == "pending":
                raise UserError("This exception is already pending.")
        self.write({"state": "pending", "resolved_by": False, "resolved_date": False})

    @api.model
    def _detect_exceptions(self, date_from, date_to, employee_ids=None):
        """Idempotently creates a pending exception for every working day
        (per the employee's own resource.calendar) in [date_from, date_to]
        where the employee has neither an hr.attendance record nor an
        approved/global leave. Deliberately reuses employee.list_leaves()
        - the exact helper the vendored payroll module's own
        _compute_leave_days uses - so "on leave" means the same thing
        here as it will once this feeds a payroll LOP rule in the Leave
        phase; a second, disagreeing definition of "on leave" would be
        worse than none.
        """
        Employee = self.env["hr.employee"].sudo()
        Attendance = self.env["hr.attendance"].sudo()
        Exception_ = self.env["bpro.attendance.exception"].sudo()

        domain = [("company_id", "in", self.env.companies.ids)]
        if employee_ids:
            domain.append(("id", "in", employee_ids))
        employees = Employee.search(domain)

        created = Exception_.browse()

        for employee in employees:
            calendar = employee.resource_calendar_id
            if not calendar:
                continue
            # list_leaves()/hr.attendance both compare against UTC - the
            # naive date range must be localized to the employee's own tz
            # first, or the boundary (esp. a single-day "yesterday" cron
            # run) can miss records near local midnight, off by the UTC
            # offset (+5:30 for India).
            tz = pytz_timezone(employee.tz or "Asia/Kolkata")
            range_start = tz.localize(datetime.combine(date_from, time.min)).astimezone(UTC).replace(tzinfo=None)
            range_end = tz.localize(datetime.combine(date_to, time.max)).astimezone(UTC).replace(tzinfo=None)
            leave_days = {
                day for day, hours, leave in employee.list_leaves(range_start, range_end, calendar=calendar)
            }
            # check_in is stored in UTC - convert back to the employee's
            # local date before comparing, or an early-morning local
            # check-in (before ~05:30 IST) would land on the previous
            # UTC calendar day and get misattributed.
            attendance_days = {
                UTC.localize(att.check_in).astimezone(tz).date()
                for att in Attendance.search([
                    ("employee_id", "=", employee.id),
                    ("check_in", ">=", range_start),
                    ("check_in", "<=", range_end),
                ])
            }
            existing_dates = {
                exc.date
                for exc in Exception_.search([
                    ("employee_id", "=", employee.id),
                    ("date", ">=", date_from),
                    ("date", "<=", date_to),
                ])
            }

            current = date_from
            while current <= date_to:
                if (
                    calendar._works_on_date(current)
                    and current not in leave_days
                    and current not in attendance_days
                    and current not in existing_dates
                ):
                    created |= Exception_.create({
                        "employee_id": employee.id,
                        "date": current,
                    })
                current += timedelta(days=1)

        return created

    @api.model
    def _cron_detect_yesterday_exceptions(self):
        yesterday = fields.Date.context_today(self) - timedelta(days=1)
        self._detect_exceptions(yesterday, yesterday)
