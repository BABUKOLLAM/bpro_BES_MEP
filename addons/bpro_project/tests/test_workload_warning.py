from odoo.tests.common import TransactionCase


class TestWorkloadWarning(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.env["bpro.policy"].create(
            {
                "company_id": cls.company.id,
                "key": "project_employee_capacity_hours",
                "numeric_value": 20.0,
            }
        )
        cls.employee_user = cls.env["res.users"].create(
            {
                "name": "Workload Assignee",
                "login": "workload-assignee@test.example",
                "email": "workload-assignee@test.example",
                "groups_id": [(4, cls.env.ref("base.group_user").id)],
            }
        )
        cls.project = cls.env["project.project"].create(
            {"name": "Workload Test Project", "allow_timesheets": True}
        )

    def _task(self, allocated_hours):
        return self.env["project.task"].create(
            {
                "name": "Workload Test Task",
                "project_id": self.project.id,
                "allocated_hours": allocated_hours,
                "user_ids": [(4, self.employee_user.id)],
            }
        )

    def test_under_threshold_has_no_warning(self):
        task = self._task(10.0)
        self.assertFalse(task.bpro_workload_warning)

    def test_over_threshold_across_open_tasks_warns(self):
        task_a = self._task(15.0)
        task_b = self._task(15.0)
        self.assertIn(self.employee_user.name, task_a.bpro_workload_warning)
        self.assertIn(self.employee_user.name, task_b.bpro_workload_warning)

    def test_closing_a_task_removes_it_from_the_workload_total(self):
        task_a = self._task(15.0)
        task_b = self._task(15.0)
        self.assertTrue(task_a.bpro_workload_warning)
        task_b.write({"state": "1_done"})
        self.assertFalse(task_a.bpro_workload_warning)

    def test_unassigned_task_has_no_warning(self):
        task = self.env["project.task"].create(
            {
                "name": "Unassigned Task",
                "project_id": self.project.id,
                "allocated_hours": 100.0,
                "user_ids": [(5, 0, 0)],
            }
        )
        self.assertFalse(task.bpro_workload_warning)
