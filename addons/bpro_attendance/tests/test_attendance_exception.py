from datetime import date, datetime, time, timedelta

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestAttendanceException(TransactionCase):
    """R5.1's unexplained-absence detection and HR review workflow."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env["hr.employee"].create({
            "name": "Exception Test Employee",
            "tz": "Asia/Kolkata",
        })
        cls.calendar = cls.employee.resource_calendar_id
        cls.Exception = cls.env["bpro.attendance.exception"]
        # Deterministic anchor: first working day on/after Mon 2026-08-10.
        day = date(2026, 8, 10)
        while not cls.calendar._works_on_date(day):
            day += timedelta(days=1)
        cls.working = []
        while len(cls.working) < 5:
            if cls.calendar._works_on_date(day):
                cls.working.append(day)
            day += timedelta(days=1)

    def _detect(self, date_from, date_to):
        return self.Exception._detect_exceptions(
            date_from, date_to, employee_ids=[self.employee.id]
        )

    def test_flags_unattended_working_days_only(self):
        # Attendance on day 0, nothing on days 1-4.
        self.env["hr.attendance"].create({
            "employee_id": self.employee.id,
            "check_in": datetime.combine(self.working[0], time(3, 30)),
            "check_out": datetime.combine(self.working[0], time(12, 30)),
        })
        created = self._detect(self.working[0], self.working[4])
        self.assertNotIn(self.working[0], created.mapped("date"))
        for day in self.working[1:5]:
            self.assertIn(day, created.mapped("date"))

    def test_approved_leave_day_not_flagged(self):
        leave_type = self.env["hr.leave.type"].create({
            "name": "Exception Test Leave",
            "requires_allocation": "no",
        })
        leave = self.env["hr.leave"].create({
            "employee_id": self.employee.id,
            "holiday_status_id": leave_type.id,
            "request_date_from": self.working[1],
            "request_date_to": self.working[1],
        })
        leave.action_approve()
        created = self._detect(self.working[1], self.working[1])
        self.assertFalse(created)

    def test_detection_is_idempotent(self):
        first = self._detect(self.working[0], self.working[2])
        self.assertTrue(first)
        again = self._detect(self.working[0], self.working[2])
        self.assertFalse(again)

    def test_resolution_workflow_guards(self):
        exception = self._detect(self.working[0], self.working[0])
        exception.action_excuse()
        self.assertEqual(exception.state, "excused")
        with self.assertRaises(UserError):
            exception.action_excuse()
        with self.assertRaises(UserError):
            exception.action_confirm_absent()
        exception.action_reset_pending()
        exception.action_confirm_absent()
        self.assertEqual(exception.state, "confirmed_absent")
