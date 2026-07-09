from odoo.tests.common import TransactionCase


class TestFieldSales(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dealer = cls.env["res.partner"].create({"name": "Test Dealer"})
        cls.employee = cls.env["hr.employee"].create({"name": "Field Rep"})

    def test_journey_plan_defaults_to_planned(self):
        plan = self.env["bpro.field.journey.plan"].create(
            {"employee_id": self.employee.id, "partner_id": self.dealer.id}
        )
        self.assertEqual(plan.state, "planned")

    def test_mark_visited(self):
        plan = self.env["bpro.field.journey.plan"].create(
            {"employee_id": self.employee.id, "partner_id": self.dealer.id}
        )
        plan.action_mark_visited()
        self.assertEqual(plan.state, "visited")

    def test_mark_missed(self):
        plan = self.env["bpro.field.journey.plan"].create(
            {"employee_id": self.employee.id, "partner_id": self.dealer.id}
        )
        plan.action_mark_missed()
        self.assertEqual(plan.state, "missed")

    def test_collection_confirmed_in_full_is_collected(self):
        plan = self.env["bpro.field.collection.plan"].create(
            {
                "employee_id": self.employee.id,
                "partner_id": self.dealer.id,
                "expected_amount": 10000.0,
                "collected_amount": 10000.0,
            }
        )
        plan.action_confirm_collection()
        self.assertEqual(plan.state, "collected")

    def test_collection_confirmed_partially_is_partial(self):
        plan = self.env["bpro.field.collection.plan"].create(
            {
                "employee_id": self.employee.id,
                "partner_id": self.dealer.id,
                "expected_amount": 10000.0,
                "collected_amount": 4000.0,
            }
        )
        plan.action_confirm_collection()
        self.assertEqual(plan.state, "partial")

    def test_collection_confirmed_with_nothing_collected_is_missed(self):
        plan = self.env["bpro.field.collection.plan"].create(
            {
                "employee_id": self.employee.id,
                "partner_id": self.dealer.id,
                "expected_amount": 10000.0,
            }
        )
        plan.action_confirm_collection()
        self.assertEqual(plan.state, "missed")

    def test_partner_outstanding_reflects_live_receivable(self):
        plan = self.env["bpro.field.collection.plan"].create(
            {
                "employee_id": self.employee.id,
                "partner_id": self.dealer.id,
                "expected_amount": 5000.0,
            }
        )
        self.assertEqual(plan.partner_outstanding, self.dealer.credit)
