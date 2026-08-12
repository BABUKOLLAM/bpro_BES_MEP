from odoo.exceptions import UserError

from .common import RecruitmentTestCommon


class TestEmployeeAsset(RecruitmentTestCommon):
    """R4.5's IT-equipment issue/return tracker - deliberately separate
    from bpro_plant's fixed-asset register."""

    def setUp(self):
        super().setUp()
        self.asset_employee = self.env["hr.employee"].create({
            "name": "Asset Test Employee", "company_id": self.company.id,
        })

    def test_asset_defaults_to_issued(self):
        asset = self.env["bpro.employee.asset"].create({
            "employee_id": self.asset_employee.id,
            "name": "Dell Latitude 5420",
            "asset_type": "laptop",
        })
        self.assertEqual(asset.state, "issued")
        self.assertFalse(asset.returned_date)

    def test_mark_returned_sets_state_and_date(self):
        asset = self.env["bpro.employee.asset"].create({
            "employee_id": self.asset_employee.id,
            "name": "Dell Latitude 5420",
            "asset_type": "laptop",
        })
        asset.action_mark_returned()
        self.assertEqual(asset.state, "returned")
        self.assertTrue(asset.returned_date)

    def test_mark_returned_twice_raises(self):
        asset = self.env["bpro.employee.asset"].create({
            "employee_id": self.asset_employee.id,
            "name": "Dell Latitude 5420",
            "asset_type": "laptop",
        })
        asset.action_mark_returned()
        with self.assertRaises(UserError):
            asset.action_mark_returned()
