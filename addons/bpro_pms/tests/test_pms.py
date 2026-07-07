from psycopg2 import IntegrityError

from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestPmsCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.corp = cls.env.ref("base.main_company")
        cls.client_a = cls.env["res.company"].create(
            {"name": "Test Client A", "parent_id": cls.corp.id}
        )
        cls.client_b = cls.env["res.company"].create(
            {"name": "Test Client B", "parent_id": cls.corp.id}
        )

        def mkuser(login, company, groups):
            return cls.env["res.users"].create(
                {
                    "name": login,
                    "login": login,
                    "company_id": company.id,
                    "company_ids": [(6, 0, [company.id])],
                    "groups_id": [(4, cls.env.ref("base.group_user").id)]
                    + [(4, cls.env.ref(g).id) for g in groups],
                }
            )

        cls.user_hr_a = mkuser("test-hr-a", cls.client_a, ["bpro_base.group_client_hr"])
        cls.user_hod_a = mkuser("test-hod-a", cls.client_a, ["bpro_base.group_hod"])
        cls.user_emp_a = mkuser("test-emp-a", cls.client_a, ["bpro_base.group_employee"])
        cls.user_hr_b = mkuser("test-hr-b", cls.client_b, ["bpro_base.group_client_hr"])

        cls.emp_hod_a = cls.env["hr.employee"].create(
            {"name": "test-hod-a", "company_id": cls.client_a.id,
             "user_id": cls.user_hod_a.id}
        )
        cls.dept_a = cls.env["hr.department"].create(
            {"name": "Test Sales", "company_id": cls.client_a.id,
             "manager_id": cls.emp_hod_a.id}
        )
        cls.emp_hod_a.department_id = cls.dept_a
        cls.emp_a = cls.env["hr.employee"].create(
            {"name": "test-emp-a", "company_id": cls.client_a.id,
             "user_id": cls.user_emp_a.id, "department_id": cls.dept_a.id}
        )
        cls.emp_a2 = cls.env["hr.employee"].create(
            {"name": "test-emp-a2", "company_id": cls.client_a.id}
        )
        cls.cycle_a = cls.env["bpro.pms.cycle"].create(
            {"name": "Test Cycle A", "date_start": "2026-07-01",
             "date_end": "2026-12-31", "company_id": cls.client_a.id}
        )


class TestGoals(TestPmsCommon):
    def test_goal_workflow(self):
        goal = self.env["bpro.pms.goal"].create(
            {"name": "Test goal", "employee_id": self.emp_a.id,
             "cycle_id": self.cycle_a.id, "company_id": self.client_a.id}
        )
        self.assertEqual(goal.state, "draft")
        self.assertEqual(goal.department_id, self.dept_a)
        self.assertEqual(goal.manager_id, self.emp_a.parent_id)
        goal.action_activate()
        self.assertEqual(goal.state, "active")
        goal.action_done()
        self.assertEqual(goal.state, "done")
        self.assertEqual(goal.progress, 100)

    @mute_logger("odoo.sql_db")
    def test_goal_progress_constraint(self):
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self.env["bpro.pms.goal"].create(
                {"name": "bad", "employee_id": self.emp_a.id, "progress": 150}
            )

    @mute_logger("odoo.sql_db")
    def test_cycle_dates_constraint(self):
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self.env["bpro.pms.cycle"].create(
                {"name": "bad", "date_start": "2026-12-31",
                 "date_end": "2026-07-01"}
            )

    def test_goal_security_scoping(self):
        Goal = self.env["bpro.pms.goal"]
        g_emp = Goal.create(
            {"name": "emp goal", "employee_id": self.emp_a.id,
             "cycle_id": self.cycle_a.id, "company_id": self.client_a.id}
        )
        Goal.create(
            {"name": "other goal", "employee_id": self.emp_a2.id,
             "cycle_id": self.cycle_a.id, "company_id": self.client_a.id}
        )
        # employee: self only
        seen = Goal.with_user(self.user_emp_a).search([])
        self.assertEqual(seen, g_emp)
        # HOD: department (both employees are in dept, emp_a2 has no dept -> excluded)
        seen_hod = Goal.with_user(self.user_hod_a).search([])
        self.assertIn(g_emp, seen_hod)
        # HR of A: both; HR of B: none
        self.assertEqual(
            Goal.with_user(self.user_hr_a).search_count([]), 2)
        self.assertEqual(
            Goal.with_user(self.user_hr_b).search_count([]), 0)


class TestAppraisals(TestPmsCommon):
    def test_appraisal_flow_and_training_needs(self):
        comp = self.env["bpro.pms.competency"].create(
            {"name": "Test Competency", "company_id": self.client_a.id}
        )
        appr = self.env["bpro.pms.appraisal"].create(
            {"employee_id": self.emp_a.id, "reviewer_id": self.emp_hod_a.id,
             "cycle_id": self.cycle_a.id, "company_id": self.client_a.id}
        )
        self.assertIn("test-emp-a", appr.name)
        need = self.env["bpro.pms.training.need"].create(
            {"employee_id": self.emp_a.id, "competency_id": comp.id,
             "appraisal_id": appr.id}
        )
        appr.action_start_self()
        appr.action_submit_review()
        appr.rating = "4"
        appr.action_done()
        self.assertEqual(appr.state, "done")
        self.assertEqual(need.state, "enrolled")

    def test_cycle_counts(self):
        self.env["bpro.pms.goal"].create(
            {"name": "g", "employee_id": self.emp_a.id,
             "cycle_id": self.cycle_a.id, "company_id": self.client_a.id}
        )
        self.env["bpro.pms.appraisal"].create(
            {"employee_id": self.emp_a.id, "reviewer_id": self.emp_hod_a.id,
             "cycle_id": self.cycle_a.id, "company_id": self.client_a.id}
        )
        self.assertEqual(self.cycle_a.goal_count, 1)
        self.assertEqual(self.cycle_a.appraisal_count, 1)
