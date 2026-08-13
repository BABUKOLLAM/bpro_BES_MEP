from datetime import date

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class TestEssScoping(TransactionCase):
    """The whole point of bpro_ess is who can see what - so that is
    what gets regression-tested: own-records scoping, the done-only
    payslip gate, the draft-only resignation write window, and the
    method-level guards on HR-only exit transitions."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        internal = cls.env.ref("base.group_user")
        employee_group = cls.env.ref("bpro_base.group_employee")

        def make(name, login):
            user = cls.env["res.users"].create({
                "name": name, "login": login, "email": f"{login}@example.com",
                "company_id": cls.company.id,
                "company_ids": [(6, 0, [cls.company.id])],
                "groups_id": [(6, 0, (employee_group | internal).ids)],
            })
            employee = cls.env["hr.employee"].create({
                "name": name, "user_id": user.id, "company_id": cls.company.id,
            })
            contract = cls.env["hr.contract"].create({
                "name": f"{name} contract", "employee_id": employee.id,
                "wage": 20000, "ctc_annual": 240000.0,
                "basic_percent": 50.0, "hra_percent": 40.0,
                "struct_id": cls.env.ref("bpro_payroll.structure_india_ctc").id,
                "date_start": date(2026, 1, 1), "state": "open",
            })
            return user, employee, contract

        cls.user_a, cls.employee_a, cls.contract_a = make("ESS Emp A", "ess_emp_a")
        cls.user_b, cls.employee_b, cls.contract_b = make("ESS Emp B", "ess_emp_b")

    def _payslip(self, employee, contract, state):
        payslip = self.env["hr.payslip"].create({
            "employee_id": employee.id, "contract_id": contract.id,
            "struct_id": self.env.ref("bpro_payroll.structure_india_ctc").id,
            "date_from": date(2026, 7, 1), "date_to": date(2026, 7, 31),
            "name": f"{employee.name} {state} slip",
        })
        payslip.compute_sheet()
        if state == "done":
            payslip.write({"state": "done"})
        return payslip

    def test_employee_sees_only_own_done_payslips(self):
        own_done = self._payslip(self.employee_a, self.contract_a, "done")
        own_draft = self._payslip(self.employee_a, self.contract_a, "draft")
        other_done = self._payslip(self.employee_b, self.contract_b, "done")
        visible = self.env["hr.payslip"].with_user(self.user_a).search([])
        self.assertIn(own_done, visible)
        self.assertNotIn(own_draft, visible, "draft slips are HR work-in-progress")
        self.assertNotIn(other_done, visible)
        # Lines of another employee's slip are unreadable too.
        self.assertFalse(
            self.env["hr.payslip.line"].with_user(self.user_a).search(
                [("slip_id", "=", other_done.id)]
            )
        )

    def test_employee_sees_only_own_attendance_exceptions(self):
        own = self.env["bpro.attendance.exception"].create({
            "employee_id": self.employee_a.id, "date": date(2026, 8, 3),
        })
        other = self.env["bpro.attendance.exception"].create({
            "employee_id": self.employee_b.id, "date": date(2026, 8, 3),
        })
        visible = self.env["bpro.attendance.exception"].with_user(self.user_a).search([])
        self.assertIn(own, visible)
        self.assertNotIn(other, visible)
        with self.assertRaises(AccessError):
            own.with_user(self.user_a).action_excuse()

    def test_employee_files_own_resignation_but_cannot_run_hr_steps(self):
        Exit = self.env["bpro.exit.request"].with_user(self.user_a)
        exit_request = Exit.create({
            "employee_id": self.employee_a.id, "reason": "self-service test",
        })
        exit_request.action_submit()
        self.assertEqual(exit_request.state, "submitted")
        # Accepting your own resignation is an HR step - blocked at
        # method level, not just hidden in the view.
        with self.assertRaises(AccessError):
            exit_request.action_accept()
        # Cannot file for a colleague either.
        with self.assertRaises(AccessError):
            Exit.create({"employee_id": self.employee_b.id})

    def test_employee_cannot_edit_after_acceptance(self):
        exit_request = self.env["bpro.exit.request"].with_user(self.user_a).create({
            "employee_id": self.employee_a.id,
        })
        exit_request.action_submit()
        exit_request.with_user(self.env.ref("base.user_admin")).sudo().action_accept()
        self.assertEqual(exit_request.state, "accepted")
        # Still readable...
        self.assertTrue(exit_request.with_user(self.user_a).read(["state"]))
        # ...but no longer writable: the F&F figures are out of the
        # employee's hands once HR accepts.
        with self.assertRaises(AccessError):
            exit_request.with_user(self.user_a).write({"reason": "changed my mind"})

    def test_employee_sees_only_own_assets(self):
        own = self.env["bpro.employee.asset"].create({
            "employee_id": self.employee_a.id, "name": "ESS Laptop A",
        })
        other = self.env["bpro.employee.asset"].create({
            "employee_id": self.employee_b.id, "name": "ESS Laptop B",
        })
        visible = self.env["bpro.employee.asset"].with_user(self.user_a).search([])
        self.assertIn(own, visible)
        self.assertNotIn(other, visible)
