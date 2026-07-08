from odoo.tests.common import TransactionCase


class TestDepartureDeactivatesUser(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.reason = cls.env["hr.departure.reason"].create({"name": "Test Departure Reason"})
        cls.user = cls.env["res.users"].create(
            {
                "name": "Departing Employee User",
                "login": "departing-employee@test.example",
                "email": "departing-employee@test.example",
                "groups_id": [(4, cls.env.ref("base.group_user").id)],
            }
        )
        cls.employee = cls.env["hr.employee"].create(
            {"name": "Departing Employee", "user_id": cls.user.id}
        )

    def _register_departure(self, employee):
        wizard = self.env["hr.departure.wizard"].with_context(
            active_id=employee.id
        ).create(
            {
                "employee_id": employee.id,
                "departure_reason_id": self.reason.id,
            }
        )
        wizard.action_register_departure()

    def test_registering_departure_deactivates_the_linked_user(self):
        self.employee.action_archive()
        self._register_departure(self.employee)
        self.assertFalse(self.user.active)

    def test_employee_with_no_linked_user_does_not_error(self):
        employee = self.env["hr.employee"].create({"name": "No User Employee"})
        employee.action_archive()
        self._register_departure(employee)
        self.assertEqual(employee.departure_reason_id, self.reason)

    def test_departure_metadata_recorded_regardless(self):
        self.employee.action_archive()
        self._register_departure(self.employee)
        self.assertEqual(self.employee.departure_reason_id, self.reason)
        self.assertTrue(self.employee.departure_date)
