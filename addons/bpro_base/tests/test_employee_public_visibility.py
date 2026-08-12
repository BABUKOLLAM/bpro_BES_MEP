from .common import BproBaseSecurityCommon


class TestEmployeePublicVisibility(BproBaseSecurityCommon):
    """hr.employee.public is the read-only directory Odoo serves to users
    who don't have full HR access (e.g. a plain Employee browsing the
    company directory) - it shares primary keys with hr.employee, but is
    a SEPARATE model with its own ir.rule records in bpro_security.xml.
    Getting hr.employee's rules right and forgetting this model's mirror
    of them would leave the directory wide open even though the "real"
    HR data is properly scoped - worth its own test file, not folded
    into test_employee_visibility.py, precisely because it's so easy to
    fix one and forget the other."""

    def test_employee_sees_only_self_in_directory(self):
        seen = self.env["hr.employee.public"].with_user(self.user_a_employee).search([])
        self.assertEqual(seen.ids, [self.employee_a_member.id])

    def test_hod_directory_view_is_scoped_to_own_department(self):
        seen = self.env["hr.employee.public"].with_user(self.user_a_hod).search([])
        seen_ids = set(seen.ids)
        self.assertIn(self.employee_a_hod.id, seen_ids)
        self.assertIn(self.employee_a_member.id, seen_ids)
        self.assertNotIn(self.employee_a2_member.id, seen_ids)
        self.assertNotIn(self.employee_b_member.id, seen_ids)

    def test_hr_admin_directory_view_is_scoped_to_own_company(self):
        seen = self.env["hr.employee.public"].with_user(self.user_a_hr).search([])
        seen_ids = set(seen.ids)
        self.assertIn(self.employee_a2_member.id, seen_ids)
        self.assertNotIn(self.employee_b_member.id, seen_ids)

    def test_super_admin_directory_view_spans_every_company(self):
        seen = self.env["hr.employee.public"].with_user(self.user_super).search([])
        seen_ids = set(seen.ids)
        self.assertIn(self.employee_a_member.id, seen_ids)
        self.assertIn(self.employee_b_member.id, seen_ids)
