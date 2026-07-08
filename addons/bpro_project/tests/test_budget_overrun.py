from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestBudgetOverrun(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.env["bpro.policy"].create(
            {
                "company_id": cls.company.id,
                "key": "project_budget_overrun_pct",
                "numeric_value": 10.0,
            }
        )
        cls.manager = cls.env["res.users"].create(
            {
                "name": "Project Manager",
                "login": "project-manager@test.example",
                "email": "project-manager@test.example",
                "groups_id": [
                    (4, cls.env.ref("base.group_user").id),
                    (4, cls.env.ref("project.group_project_manager").id),
                ],
            }
        )
        cls.employee_user = cls.env["res.users"].create(
            {
                "name": "Task Assignee",
                "login": "task-assignee@test.example",
                "email": "task-assignee@test.example",
                "groups_id": [(4, cls.env.ref("base.group_user").id)],
            }
        )
        cls.employee = cls.env["hr.employee"].create(
            {"name": "Task Assignee", "user_id": cls.employee_user.id}
        )
        cls.project = cls.env["project.project"].create(
            {"name": "Budget Test Project", "allow_timesheets": True}
        )

    def _task(self, allocated_hours=10.0):
        return self.env["project.task"].create(
            {
                "name": "Budget Test Task",
                "project_id": self.project.id,
                "allocated_hours": allocated_hours,
                "user_ids": [(4, self.employee_user.id)],
            }
        )

    def _log_hours(self, task, hours):
        self.env["account.analytic.line"].create(
            {
                "name": "Work done",
                "project_id": self.project.id,
                "task_id": task.id,
                "employee_id": self.employee.id,
                "unit_amount": hours,
            }
        )

    def test_small_overrun_does_not_block_closing(self):
        task = self._task(allocated_hours=10.0)
        self._log_hours(task, 10.5)
        self.assertEqual(task.approval_state, "none")
        task.write({"state": "1_done"})
        self.assertEqual(task.state, "1_done")

    def test_large_overrun_blocks_closing(self):
        task = self._task(allocated_hours=10.0)
        self._log_hours(task, 15.0)
        self.assertEqual(task.approval_state, "pending")
        with self.assertRaises(UserError):
            task.write({"state": "1_done"})

    def test_manager_approval_unblocks_closing(self):
        task = self._task(allocated_hours=10.0)
        self._log_hours(task, 15.0)
        with self.assertRaises(UserError):
            task.write({"state": "1_done"})
        task.with_user(self.manager).action_approve()
        task.write({"state": "1_done"})
        self.assertEqual(task.state, "1_done")

    def test_unallocated_task_never_triggers_overrun(self):
        task = self._task(allocated_hours=0.0)
        self._log_hours(task, 100.0)
        self.assertEqual(task.approval_state, "none")
        task.write({"state": "1_done"})
        self.assertEqual(task.state, "1_done")

    def test_removing_the_overrunning_line_reopens_the_gate(self):
        task = self._task(allocated_hours=10.0)
        self._log_hours(task, 15.0)
        self.assertEqual(task.approval_state, "pending")
        task.timesheet_ids.unlink()
        self.assertEqual(task.approval_state, "none")
        task.write({"state": "1_done"})
        self.assertEqual(task.state, "1_done")
