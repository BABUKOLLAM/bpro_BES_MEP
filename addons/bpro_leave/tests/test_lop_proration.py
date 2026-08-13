from datetime import date, timedelta

from odoo.tests.common import TransactionCase


class TestLopProration(TransactionCase):
    """R5.2's LOP factor and its effect on the payslip - proration at
    the earnings source so PF (via BASIC) and ESI (via GROSS) follow
    actual earned wages, per the confirmed statutory-correct choice."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.struct = cls.env.ref("bpro_payroll.structure_india_ctc")
        cls.lop_type = cls.env.ref("bpro_leave.leave_type_lop")
        cls.date_from, cls.date_to = date(2026, 8, 1), date(2026, 8, 31)

    def _make_employee(self, name):
        employee = self.env["hr.employee"].create({
            "name": name, "tz": "Asia/Kolkata",
        })
        # Basic of 10k sits under the PF wage ceiling, so PF proration
        # is visible - a ceiling-capped basic would hide it entirely.
        contract = self.env["hr.contract"].create({
            "name": f"{name} contract",
            "employee_id": employee.id,
            "wage": 20000,
            "ctc_annual": 240000.0,
            "basic_percent": 50.0,
            "hra_percent": 40.0,
            "struct_id": self.struct.id,
            "date_start": date(2026, 1, 1),
            "state": "open",
        })
        return employee, contract

    def _working_days(self, contract):
        days, current = [], self.date_from
        while current <= self.date_to:
            if contract.resource_calendar_id._works_on_date(current):
                days.append(current)
            current += timedelta(days=1)
        return days

    def _payslip(self, employee, contract):
        payslip = self.env["hr.payslip"].create({
            "employee_id": employee.id,
            "contract_id": contract.id,
            "struct_id": self.struct.id,
            "date_from": self.date_from,
            "date_to": self.date_to,
            "name": f"slip {employee.name}",
        })
        payslip.compute_sheet()
        return {line.code: line.total for line in payslip.line_ids}

    def test_factor_unions_exceptions_and_lop_leave(self):
        employee, contract = self._make_employee("LOP Union Employee")
        working = self._working_days(contract)
        # 2 confirmed exceptions + 2-day LOP leave overlapping one of
        # them: the union is 3 distinct days, not 4.
        for day in (working[2], working[5]):
            self.env["bpro.attendance.exception"].create({
                "employee_id": employee.id, "date": day,
                "state": "confirmed_absent",
            })
        leave = self.env["hr.leave"].create({
            "employee_id": employee.id,
            "holiday_status_id": self.lop_type.id,
            "request_date_from": working[5],
            "request_date_to": working[6],
        })
        leave.action_approve()

        payslip = self.env["hr.payslip"].create({
            "employee_id": employee.id, "contract_id": contract.id,
            "struct_id": self.struct.id, "date_from": self.date_from,
            "date_to": self.date_to, "name": "factor slip",
        })
        factor = payslip.bpro_lop_factor(employee, contract)
        self.assertAlmostEqual(factor, (len(working) - 3) / len(working), places=9)

    def test_payslip_prorates_earnings_pf_and_esi(self):
        employee, contract = self._make_employee("LOP Slip Employee")
        working = self._working_days(contract)
        for day in working[:3]:
            self.env["bpro.attendance.exception"].create({
                "employee_id": employee.id, "date": day,
                "state": "confirmed_absent",
            })
        lines = self._payslip(employee, contract)
        factor = (len(working) - 3) / len(working)
        basic = 10000.0 * factor
        gross = basic * 1.4
        self.assertAlmostEqual(lines["BASIC"], basic, places=2)
        self.assertAlmostEqual(lines["HRA"], basic * 0.4, places=2)
        self.assertAlmostEqual(lines["GROSS"], gross, places=2)
        self.assertAlmostEqual(
            lines["PF_EE"],
            min(basic, self.company.pf_wage_ceiling) * self.company.pf_employee_rate / 100.0,
            places=2,
        )
        if gross <= self.company.esi_wage_threshold:
            self.assertAlmostEqual(
                lines["ESI_EE"], gross * self.company.esi_employee_rate / 100.0, places=2
            )

    def test_full_attendance_and_paid_leave_unaffected(self):
        employee, contract = self._make_employee("Full Pay Employee")
        working = self._working_days(contract)
        # An approved PAID (non-LOP) leave must not reduce pay.
        sick_type = self.env.ref("bpro_leave.leave_type_sick")
        # Explicit date_from: the default is "today", which would
        # post-date the early-August leave day whenever the suite runs
        # later in the year, making the allocation invalid for it.
        self.env["hr.leave.allocation"].create({
            "name": "sick alloc", "employee_id": employee.id,
            "holiday_status_id": sick_type.id, "number_of_days": 12,
            "state": "confirm", "date_from": date(2026, 1, 1),
        }).action_approve()
        leave = self.env["hr.leave"].create({
            "employee_id": employee.id,
            "holiday_status_id": sick_type.id,
            "request_date_from": working[4],
            "request_date_to": working[4],
        })
        leave.action_approve()
        lines = self._payslip(employee, contract)
        self.assertAlmostEqual(lines["BASIC"], 10000.0, places=2)
        self.assertAlmostEqual(lines["GROSS"], 14000.0, places=2)
