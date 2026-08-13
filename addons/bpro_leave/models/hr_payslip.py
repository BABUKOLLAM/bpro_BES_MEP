from datetime import timedelta

from odoo import models


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    def bpro_lop_factor(self, employee, contract):
        """Payable fraction of this payslip's period:
        (working_days - lop_days) / working_days.

        LOP days are the union (a set of dates, so a day that is both a
        confirmed attendance exception AND covered by an approved
        Loss-of-Pay leave counts once, not twice) of:
        * bpro.attendance.exception records HR confirmed as absent
          (bpro_attendance R5.1 - pending/excused ones don't dock pay,
          per the client's flag-for-review-first decision), and
        * approved hr.leave days whose type is flagged bpro_is_lop_type.

        Working days are per the contract's own resource calendar, so a
        6-day-week factory worker and a 5-day-week office employee each
        prorate against their own denominator.

        Lives here as a real method (not inline salary-rule code) because
        rule code runs under safe_eval with no datetime access - and so
        the date logic is unit-testable outside a payslip run.
        """
        lop_days, working_days = self.bpro_lop_days(employee, contract)
        if not working_days:
            return 1.0
        return max(working_days - lop_days, 0) / working_days

    def bpro_lop_days(self, employee, contract):
        """(lop_day_count, working_day_count) for this payslip's period -
        split out of bpro_lop_factor so statutory filings can report the
        day counts themselves (EPFO's ECR wants NCP days, ESIC wants
        days worked) from the SAME definition the pay proration uses -
        a filing that disagreed with the payslip would be worse than
        no filing."""
        self.ensure_one()
        calendar = contract.resource_calendar_id
        if not calendar:
            return 0, 0

        working_days = []
        current = self.date_from
        while current <= self.date_to:
            if calendar._works_on_date(current):
                working_days.append(current)
            current += timedelta(days=1)
        if not working_days:
            return 0, 0
        working_set = set(working_days)

        lop_dates = set()

        exceptions = self.env["bpro.attendance.exception"].sudo().search([
            ("employee_id", "=", employee.id),
            ("state", "=", "confirmed_absent"),
            ("date", ">=", self.date_from),
            ("date", "<=", self.date_to),
        ])
        lop_dates.update(exc.date for exc in exceptions if exc.date in working_set)

        lop_leaves = self.env["hr.leave"].sudo().search([
            ("employee_id", "=", employee.id),
            ("state", "=", "validate"),
            ("holiday_status_id.bpro_is_lop_type", "=", True),
            ("request_date_from", "<=", self.date_to),
            ("request_date_to", ">=", self.date_from),
        ])
        for leave in lop_leaves:
            day = max(leave.request_date_from, self.date_from)
            last = min(leave.request_date_to, self.date_to)
            while day <= last:
                if day in working_set:
                    lop_dates.add(day)
                day += timedelta(days=1)

        return len(lop_dates), len(working_set)
