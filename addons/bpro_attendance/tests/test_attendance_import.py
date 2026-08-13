import base64
from datetime import date, timedelta

from odoo.tests.common import TransactionCase


class TestAttendanceImport(TransactionCase):
    """R5.1's device-agnostic punch-log import - the permanent version
    of the shell verification run at build time."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env["hr.employee"].create({
            "name": "Import Test Employee",
            "barcode": "IMPTEST1",
            "tz": "Asia/Kolkata",
        })
        # First working day per the employee's calendar from a fixed
        # Monday anchor, so the test is deterministic regardless of
        # which weekday the suite runs on.
        calendar = cls.employee.resource_calendar_id
        day = date(2026, 8, 10)
        while not calendar._works_on_date(day):
            day += timedelta(days=1)
        cls.working_day = day

    def _import(self, csv_text):
        wizard = self.env["bpro.attendance.import"].create({
            "attachment": base64.b64encode(csv_text.encode("utf-8")),
            "filename": "test.csv",
        })
        wizard.action_import()
        return wizard

    def test_import_matches_badge_and_converts_ist_to_utc(self):
        day = self.working_day.isoformat()
        wizard = self._import(
            "badge_id,date,check_in,check_out\n"
            f"IMPTEST1,{day},09:00,18:00\n"
        )
        attendance = self.env["hr.attendance"].search(
            [("employee_id", "=", self.employee.id)]
        )
        self.assertEqual(len(attendance), 1, wizard.result_summary)
        # 09:00 IST is 03:30 UTC - storing the device-local time as-is
        # would silently shift every record by 5.5 hours.
        self.assertEqual(str(attendance.check_in), f"{day} 03:30:00")
        # 9h span minus the standard calendar's 1h lunch deduction.
        self.assertEqual(attendance.worked_hours, 8.0)

    def test_unmatched_badge_and_bad_rows_reported_not_dropped(self):
        day = self.working_day.isoformat()
        wizard = self._import(
            "badge_id,date,check_in,check_out\n"
            f"NOSUCHBADGE,{day},09:00,18:00\n"
            f"IMPTEST1,{day},,\n"
        )
        self.assertFalse(
            self.env["hr.attendance"].search([("employee_id", "=", self.employee.id)])
        )
        self.assertIn("NOSUCHBADGE", wizard.result_summary)
        self.assertIn("missing check_in", wizard.result_summary)

    def test_reimport_skips_duplicates(self):
        day = self.working_day.isoformat()
        csv_text = (
            "badge_id,date,check_in,check_out\n"
            f"IMPTEST1,{day},09:00,18:00\n"
        )
        self._import(csv_text)
        wizard = self._import(csv_text)
        self.assertEqual(
            len(self.env["hr.attendance"].search([("employee_id", "=", self.employee.id)])),
            1,
        )
        self.assertIn("already recorded", wizard.result_summary)
