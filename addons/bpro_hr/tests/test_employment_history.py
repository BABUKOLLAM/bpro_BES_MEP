from odoo.tests.common import TransactionCase


class TestEmploymentHistory(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.dept_a = cls.env["hr.department"].create({"name": "Dept A"})
        cls.dept_b = cls.env["hr.department"].create({"name": "Dept B"})
        cls.manager = cls.env["hr.employee"].create({"name": "Manager"})

    def test_creating_an_employee_opens_an_initial_history_row(self):
        employee = self.env["hr.employee"].create(
            {"name": "New Hire", "department_id": self.dept_a.id}
        )
        self.assertEqual(len(employee.bpro_employment_history_ids), 1)
        row = employee.bpro_employment_history_ids
        self.assertEqual(row.department_id, self.dept_a)
        self.assertFalse(row.date_end, "the initial period must still be open")

    def test_department_transfer_closes_old_row_and_opens_a_new_one(self):
        employee = self.env["hr.employee"].create(
            {"name": "Transferee", "department_id": self.dept_a.id}
        )
        employee.department_id = self.dept_b.id
        self.assertEqual(len(employee.bpro_employment_history_ids), 2)
        old_row = employee.bpro_employment_history_ids.filtered(
            lambda r: r.department_id == self.dept_a
        )
        new_row = employee.bpro_employment_history_ids.filtered(
            lambda r: r.department_id == self.dept_b
        )
        self.assertTrue(old_row.date_end, "the superseded period must be closed")
        self.assertFalse(new_row.date_end, "the new period must be open")

    def test_manager_change_is_tracked_even_though_native_chatter_ignores_it(self):
        employee = self.env["hr.employee"].create({"name": "Reportee"})
        employee.parent_id = self.manager.id
        self.assertEqual(len(employee.bpro_employment_history_ids), 2)
        self.assertEqual(
            employee.bpro_employment_history_ids.sorted("date_start")[-1].manager_id,
            self.manager,
        )

    def test_unrelated_field_write_does_not_create_a_history_row(self):
        employee = self.env["hr.employee"].create({"name": "Unrelated Write Test"})
        employee.work_phone = "+1 555 0100"
        self.assertEqual(len(employee.bpro_employment_history_ids), 1)

    def test_rewriting_the_same_department_does_not_duplicate_a_row(self):
        employee = self.env["hr.employee"].create(
            {"name": "No-op Write Test", "department_id": self.dept_a.id}
        )
        employee.department_id = self.dept_a.id
        self.assertEqual(len(employee.bpro_employment_history_ids), 1)

    def test_transferring_department_and_manager_together_creates_one_row(self):
        employee = self.env["hr.employee"].create(
            {"name": "Combined Change Test", "department_id": self.dept_a.id}
        )
        employee.write({"department_id": self.dept_b.id, "parent_id": self.manager.id})
        self.assertEqual(
            len(employee.bpro_employment_history_ids),
            2,
            "one business event changing two fields must produce one new row, "
            "not one per field",
        )
