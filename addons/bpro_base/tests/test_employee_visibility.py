from .common import BproBaseSecurityCommon


class TestEmployeeVisibility(BproBaseSecurityCommon):
    """The actual thing this module exists to guarantee: what hr.employee
    records a user in each tier can see. Every test here checks both
    directions - that the right records ARE visible and that the wrong
    ones AREN'T - since a rule that's too permissive is a data leak and
    a rule that's too restrictive breaks the product; only testing one
    direction would miss half of that."""

    def test_employee_sees_only_self(self):
        seen = self.env["hr.employee"].with_user(self.user_a_employee).search([])
        self.assertEqual(seen, self.employee_a_member)

    def test_hod_sees_own_department_but_not_other_departments_same_company(self):
        seen = self.env["hr.employee"].with_user(self.user_a_hod).search([])
        self.assertIn(self.employee_a_hod, seen)
        self.assertIn(self.employee_a_member, seen)
        self.assertNotIn(
            self.employee_a2_member, seen,
            "HOD of Dept A saw an employee from Dept A2 - the rule scoped "
            "to company, not department.",
        )

    def test_hod_does_not_see_another_companys_employees(self):
        seen = self.env["hr.employee"].with_user(self.user_a_hod).search([])
        self.assertNotIn(self.employee_b_hod, seen)
        self.assertNotIn(self.employee_b_member, seen)

    def test_hr_admin_sees_entire_own_company_across_departments(self):
        seen = self.env["hr.employee"].with_user(self.user_a_hr).search([])
        self.assertIn(self.employee_a_hod, seen)
        self.assertIn(self.employee_a_member, seen)
        self.assertIn(
            self.employee_a2_member, seen,
            "HR Admin must see every department in their own company, "
            "not just the one their own test fixture happens to sit in.",
        )

    def test_hr_admin_does_not_see_another_companys_employees(self):
        # The exact bug class the project's own history has already hit
        # once ("fix multi-tenant data isolation") - a Client HR Admin
        # for Company A reaching Company B's employee data would be a
        # real cross-tenant leak, not a cosmetic gap.
        seen = self.env["hr.employee"].with_user(self.user_a_hr).search([])
        self.assertNotIn(self.employee_b_hod, seen)
        self.assertNotIn(self.employee_b_member, seen)

    def test_super_admin_sees_every_company(self):
        seen = self.env["hr.employee"].with_user(self.user_super).search([])
        self.assertIn(self.employee_a_hod, seen)
        self.assertIn(self.employee_a_member, seen)
        self.assertIn(self.employee_a2_member, seen)
        self.assertIn(self.employee_b_hod, seen)
        self.assertIn(self.employee_b_member, seen)

    def test_employee_cannot_read_a_colleagues_record_directly(self):
        # search() scoping is necessary but not sufficient - confirm the
        # rule also blocks a direct read()/browse() of a known id, not
        # just filtering it out of an unscoped search. employee_a_hod is
        # a genuine colleague here, not user_a_employee's own record
        # (that's employee_a_member) - reading their own record is
        # supposed to succeed, so asserting against it would prove
        # nothing about this rule.
        from odoo.exceptions import AccessError
        with self.assertRaises(AccessError):
            self.employee_a_hod.with_user(self.user_a_employee).read(["name"])
