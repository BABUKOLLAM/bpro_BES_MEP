from datetime import date, timedelta

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestExitWorkflow(TransactionCase):
    """R5.3's separation workflow, clearance enforcement and F&F math."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.today = date.today()

    def _make_employee(self, name, login, service_years):
        user = self.env["res.users"].create({
            "name": name, "login": login, "email": f"{login}@example.com",
        })
        employee = self.env["hr.employee"].create({
            "name": name, "user_id": user.id, "company_id": self.company.id,
        })
        self.env["hr.contract"].create({
            "name": f"{name} contract", "employee_id": employee.id,
            "wage": 20000, "ctc_annual": 240000.0,
            "basic_percent": 50.0, "hra_percent": 40.0,
            "date_start": self.today - timedelta(days=int(service_years * 365.25)),
            "state": "open",
        })
        return employee, user

    def _accepted_exit(self, employee):
        exit_request = self.env["bpro.exit.request"].create({
            "employee_id": employee.id, "reason": "test",
        })
        exit_request.action_submit()
        exit_request.action_accept()
        return exit_request

    def test_accept_sets_lwd_and_creates_standard_clearance(self):
        employee, _ = self._make_employee("Exit Accept Emp", "exit_accept", 6.59)
        exit_request = self._accepted_exit(employee)
        self.assertEqual(
            exit_request.last_working_day,
            exit_request.accepted_date + timedelta(days=exit_request.notice_days),
        )
        self.assertEqual(
            sorted(exit_request.clearance_line_ids.mapped("line_type")),
            ["asset", "finance", "hod", "it"],
        )

    def test_gratuity_rounds_up_past_six_months(self):
        # 6 years 7 months of service: fraction > 6 months counts as a
        # full year per the Payment of Gratuity Act, so 7 years.
        employee, _ = self._make_employee("Gratuity Emp", "exit_gratuity", 6.59)
        exit_request = self._accepted_exit(employee)
        exit_request.action_compute_settlement()
        self.assertEqual(exit_request.gratuity_years, 7)
        self.assertAlmostEqual(
            exit_request.gratuity_amount, 15.0 / 26.0 * 10000.0 * 7, places=2
        )

    def test_gratuity_zero_below_five_years(self):
        employee, _ = self._make_employee("Short Service Emp", "exit_short", 3)
        exit_request = self._accepted_exit(employee)
        exit_request.action_compute_settlement()
        self.assertEqual(exit_request.gratuity_years, 0)
        self.assertEqual(exit_request.gratuity_amount, 0.0)

    def test_el_encashment_from_allocation_balance(self):
        employee, _ = self._make_employee("EL Emp", "exit_el", 6)
        el_type = self.env.ref("bpro_leave.leave_type_earned")
        self.env["hr.leave.allocation"].create({
            "name": "el alloc", "employee_id": employee.id,
            "holiday_status_id": el_type.id, "number_of_days": 20,
            "state": "confirm",
        }).action_approve()
        exit_request = self._accepted_exit(employee)
        exit_request.action_compute_settlement()
        self.assertAlmostEqual(exit_request.el_balance_days, 20.0, places=2)
        self.assertAlmostEqual(
            exit_request.el_encashment_amount, 20.0 * 10000.0 / 26.0, places=2
        )

    def test_notice_shortfall_recovery(self):
        employee, _ = self._make_employee("Notice Emp", "exit_notice", 6)
        exit_request = self._accepted_exit(employee)
        exit_request.last_working_day = exit_request.accepted_date + timedelta(days=10)
        exit_request.action_compute_settlement()
        self.assertEqual(exit_request.notice_shortfall_days, exit_request.notice_days - 10)
        self.assertAlmostEqual(
            exit_request.notice_recovery_amount,
            exit_request.notice_shortfall_days * 14000.0 / 30.0,
            places=2,
        )

    def test_asset_clearance_enforced_against_register(self):
        employee, _ = self._make_employee("Asset Emp", "exit_asset", 6)
        asset = self.env["bpro.employee.asset"].create({
            "employee_id": employee.id, "name": "Test Laptop",
        })
        exit_request = self._accepted_exit(employee)
        asset_line = exit_request.clearance_line_ids.filtered(
            lambda line: line.line_type == "asset"
        )
        with self.assertRaises(UserError):
            asset_line.action_mark_done()
        asset.action_mark_returned()
        asset_line.action_mark_done()
        self.assertEqual(asset_line.state, "done")

    def test_settle_blocked_until_clearance_done_and_close_offboards(self):
        employee, user = self._make_employee("Close Emp", "exit_close", 6)
        exit_request = self._accepted_exit(employee)
        with self.assertRaises(UserError):
            exit_request.action_settle()
        for line in exit_request.clearance_line_ids:
            line.action_mark_done()
        exit_request.action_settle()
        self.assertEqual(exit_request.state, "settled")
        self.assertTrue(exit_request.settlement_computed)
        exit_request.action_close()
        self.assertEqual(exit_request.state, "closed")
        self.assertFalse(employee.active)
        self.assertFalse(user.active)
        self.assertEqual(employee.departure_date, exit_request.last_working_day)
