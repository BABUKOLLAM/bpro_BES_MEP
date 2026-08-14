from datetime import date, timedelta

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestShifts(TransactionCase):
    """R6.6 - dated shift assignments keep the employee's working
    calendar current, with overlap protection."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.shift_a = cls.env.ref("bpro_shifts.calendar_shift_a")
        cls.shift_b = cls.env.ref("bpro_shifts.calendar_shift_b")
        cls.employee = cls.env["hr.employee"].create({
            "name": "Shift Test Employee", "tz": "Asia/Kolkata",
        })
        cls.today = date.today()

    def test_current_assignment_applies_immediately(self):
        self.env["bpro.shift.assignment"].create({
            "employee_id": self.employee.id,
            "calendar_id": self.shift_a.id,
            "date_from": self.today,
        })
        self.assertEqual(self.employee.resource_calendar_id, self.shift_a)
        # Seeded shift pattern: Mon-Sat working, Sunday off.
        monday = self.today + timedelta(days=(7 - self.today.weekday()) % 7)
        sunday = monday + timedelta(days=6)
        self.assertTrue(self.shift_a._works_on_date(monday))
        self.assertFalse(self.shift_a._works_on_date(sunday))

    def test_future_assignment_waits_for_cron(self):
        original = self.employee.resource_calendar_id
        self.env["bpro.shift.assignment"].create({
            "employee_id": self.employee.id,
            "calendar_id": self.shift_b.id,
            "date_from": self.today + timedelta(days=7),
        })
        self.assertEqual(self.employee.resource_calendar_id, original)

    def test_cron_applies_covering_assignment(self):
        self.env["bpro.shift.assignment"].create({
            "employee_id": self.employee.id,
            "calendar_id": self.shift_b.id,
            "date_from": self.today - timedelta(days=1),
        })
        # Simulate someone having flipped the calendar manually.
        self.employee.resource_calendar_id = self.shift_a
        self.env["bpro.shift.assignment"]._cron_apply_todays_shifts()
        self.assertEqual(self.employee.resource_calendar_id, self.shift_b)

    def test_overlap_rejected(self):
        self.env["bpro.shift.assignment"].create({
            "employee_id": self.employee.id,
            "calendar_id": self.shift_a.id,
            "date_from": self.today,
            "date_to": self.today + timedelta(days=30),
        })
        with self.assertRaises(ValidationError):
            self.env["bpro.shift.assignment"].create({
                "employee_id": self.employee.id,
                "calendar_id": self.shift_b.id,
                "date_from": self.today + timedelta(days=10),
            })
        # Non-overlapping (after the first ends) is fine.
        self.env["bpro.shift.assignment"].create({
            "employee_id": self.employee.id,
            "calendar_id": self.shift_b.id,
            "date_from": self.today + timedelta(days=31),
        })
