from odoo.tests.common import TransactionCase


class TestGroupHierarchy(TransactionCase):
    """The four tiers are meant to nest (Super Admin > Client HR > HOD >
    Employee) via implied_ids, not stand as four independent groups a
    user could be assigned in isolation. If that chain ever breaks -
    e.g. a future edit to bpro_security.xml drops an implied_ids entry -
    every downstream ir.rule that assumes "HR admins are also HODs" or
    "HODs are also employees" would silently stop matching for anyone
    only assigned the top-tier group directly."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_employee = cls.env.ref("bpro_base.group_employee")
        cls.group_hod = cls.env.ref("bpro_base.group_hod")
        cls.group_client_hr = cls.env.ref("bpro_base.group_client_hr")
        cls.group_super_admin = cls.env.ref("bpro_base.group_super_admin")

    def _user_with_group(self, group):
        internal_user = self.env.ref("base.group_user")
        return self.env["res.users"].create({
            "name": f"hierarchy test {group.name}",
            "login": f"hierarchy_test_{group.id}",
            "email": f"hierarchy_test_{group.id}@example.com",
            "groups_id": [(6, 0, (group | internal_user).ids)],
        })

    def test_hod_implies_employee(self):
        user = self._user_with_group(self.group_hod)
        self.assertIn(user, self.group_employee.users)

    def test_client_hr_implies_hod_and_employee(self):
        user = self._user_with_group(self.group_client_hr)
        self.assertIn(user, self.group_hod.users)
        self.assertIn(user, self.group_employee.users)

    def test_super_admin_implies_the_entire_chain(self):
        user = self._user_with_group(self.group_super_admin)
        self.assertIn(user, self.group_client_hr.users)
        self.assertIn(user, self.group_hod.users)
        self.assertIn(user, self.group_employee.users)

    def test_employee_does_not_imply_anything_upward(self):
        # The chain only runs one direction - being an Employee must not
        # grant HOD/HR/Super Admin scope. Not a realistic misconfiguration
        # to worry about causing itself, but a cheap, worthwhile guard
        # against ever getting implied_ids backwards on this record.
        user = self._user_with_group(self.group_employee)
        self.assertNotIn(user, self.group_hod.users)
        self.assertNotIn(user, self.group_client_hr.users)
        self.assertNotIn(user, self.group_super_admin.users)
