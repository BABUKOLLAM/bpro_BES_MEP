from odoo.tests.common import TransactionCase


class BproBaseSecurityCommon(TransactionCase):
    """Two companies, each with one department and two employees (a HOD
    who manages the department and a regular report), plus one test user
    per tier of the four-tier role model. Every visibility test in this
    suite reuses this same fixture rather than building its own, so a
    failure in one test can't be explained away as "that test's setup
    was wrong" - they're all looking at the same data."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company_a = cls.env["res.company"].create({"name": "bpro Test Co A"})
        cls.company_b = cls.env["res.company"].create({"name": "bpro Test Co B"})

        group_employee = cls.env.ref("bpro_base.group_employee")
        group_hod = cls.env.ref("bpro_base.group_hod")
        group_client_hr = cls.env.ref("bpro_base.group_client_hr")
        group_super_admin = cls.env.ref("bpro_base.group_super_admin")

        internal_user = cls.env.ref("base.group_user")

        def _user(login, company, groups):
            # base.group_user (Internal User) is required alongside the
            # bpro tier group - without it the user falls outside every
            # ACL and ir.rule these tests exist to check, and fails with
            # a generic AccessError before the rule scoping is even
            # reached. Every real employee/HOD/HR-admin/super-admin in
            # this system is an Internal User; a bare bpro group with no
            # user-type group isn't a configuration that exists in
            # production, so this isn't a workaround - it's the fixture
            # matching reality.
            return cls.env["res.users"].create({
                "name": login,
                "login": login,
                "email": f"{login}@example.com",
                "company_id": company.id if company else cls.env.company.id,
                "company_ids": [(6, 0, [company.id] if company else [cls.env.company.id])],
                "groups_id": [(6, 0, (groups | internal_user).ids)],
            })

        # ---- Company A: department with a HOD and a regular employee ----
        cls.user_a_hod = _user("bpro_test_a_hod", cls.company_a, group_hod)
        cls.user_a_employee = _user("bpro_test_a_employee", cls.company_a, group_employee)
        cls.user_a_hr = _user("bpro_test_a_hr", cls.company_a, group_client_hr)

        cls.dept_a = cls.env["hr.department"].create({
            "name": "Dept A", "company_id": cls.company_a.id,
        })
        cls.employee_a_hod = cls.env["hr.employee"].create({
            "name": "A HOD", "company_id": cls.company_a.id,
            "department_id": cls.dept_a.id, "user_id": cls.user_a_hod.id,
        })
        cls.dept_a.manager_id = cls.employee_a_hod
        cls.employee_a_member = cls.env["hr.employee"].create({
            "name": "A Member", "company_id": cls.company_a.id,
            "department_id": cls.dept_a.id, "user_id": cls.user_a_employee.id,
        })

        # ---- Company B: separate department, separate people ----
        cls.user_b_hod = _user("bpro_test_b_hod", cls.company_b, group_hod)
        cls.user_b_hr = _user("bpro_test_b_hr", cls.company_b, group_client_hr)

        cls.dept_b = cls.env["hr.department"].create({
            "name": "Dept B", "company_id": cls.company_b.id,
        })
        cls.employee_b_hod = cls.env["hr.employee"].create({
            "name": "B HOD", "company_id": cls.company_b.id,
            "department_id": cls.dept_b.id, "user_id": cls.user_b_hod.id,
        })
        cls.dept_b.manager_id = cls.employee_b_hod
        cls.employee_b_member = cls.env["hr.employee"].create({
            "name": "B Member", "company_id": cls.company_b.id,
            "department_id": cls.dept_b.id,
        })

        # A second department INSIDE company A, so the HOD-scoping test
        # can prove "own department only" means something narrower than
        # "own company" - not just incidentally correct because there's
        # only one department to see.
        cls.dept_a2 = cls.env["hr.department"].create({
            "name": "Dept A2", "company_id": cls.company_a.id,
        })
        cls.employee_a2_member = cls.env["hr.employee"].create({
            "name": "A2 Member", "company_id": cls.company_a.id,
            "department_id": cls.dept_a2.id,
        })

        # Super Admin: real bpro Super Admins manage multiple client
        # companies, so - matching how one would actually be configured -
        # this user's allowed companies include both test companies, not
        # just one. The rule_super_admin_all domain is (1,=,1); this
        # confirms that isn't being silently narrowed by Odoo's own
        # multi-company allowed-company filtering on top of it.
        cls.user_super = cls.env["res.users"].create({
            "name": "bpro_test_super", "login": "bpro_test_super",
            "email": "bpro_test_super@example.com",
            "company_id": cls.company_a.id,
            "company_ids": [(6, 0, [cls.company_a.id, cls.company_b.id])],
            "groups_id": [(6, 0, group_super_admin.ids)],
        })
