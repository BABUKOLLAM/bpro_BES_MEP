from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestOwnershipConstraint(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.brand = cls.env["fleet.vehicle.model.brand"].create({"name": "Test Brand"})
        cls.model = cls.env["fleet.vehicle.model"].create(
            {"name": "Test Model", "brand_id": cls.brand.id}
        )
        cls.transporter = cls.env["res.partner"].create({"name": "Test Transporter"})
        cls.expense_account = cls.env["account.account"].search(
            [("account_type", "=", "expense")], limit=1
        )
        if not cls.expense_account:
            cls.env["account.chart.template"].try_loading(
                "generic_coa", cls.company, install_demo=False
            )
            cls.expense_account = cls.env["account.account"].search(
                [("account_type", "=", "expense")], limit=1
            )

    def _vehicle(self, **overrides):
        vals = {"model_id": self.model.id}
        vals.update(overrides)
        return self.env["fleet.vehicle"].create(vals)

    def test_owned_vehicle_needs_no_transporter(self):
        vehicle = self._vehicle(bpro_ownership_type="owned")
        self.assertEqual(vehicle.bpro_ownership_type, "owned")

    def test_hired_vehicle_without_transporter_is_rejected(self):
        with self.assertRaises(ValidationError):
            self._vehicle(bpro_ownership_type="hired")

    def test_hired_vehicle_without_expense_account_is_rejected(self):
        with self.assertRaises(ValidationError):
            self._vehicle(
                bpro_ownership_type="hired", bpro_transporter_id=self.transporter.id
            )

    def test_hired_vehicle_with_both_succeeds(self):
        vehicle = self._vehicle(
            bpro_ownership_type="hired",
            bpro_transporter_id=self.transporter.id,
            bpro_trip_expense_account_id=self.expense_account.id,
            bpro_trip_rate=1500.0,
        )
        self.assertEqual(vehicle.bpro_transporter_id, self.transporter)

    def test_switching_owned_to_hired_without_transporter_is_rejected(self):
        vehicle = self._vehicle(bpro_ownership_type="owned")
        with self.assertRaises(ValidationError):
            vehicle.bpro_ownership_type = "hired"
