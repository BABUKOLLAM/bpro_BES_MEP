from odoo.tests.common import TransactionCase


class TestPlantAssetDepreciation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.env["account.chart.template"].try_loading(
            "generic_coa", cls.company, install_demo=False
        )
        expense_account = cls.env["account.account"].search(
            [("account_type", "=", "expense"), ("company_ids", "in", cls.company.id)],
            limit=1,
        )
        accumulated_account = cls.env["account.account"].search(
            [
                ("account_type", "=", "asset_non_current"),
                ("company_ids", "in", cls.company.id),
            ],
            limit=1,
        )
        cls.expense_account = expense_account
        cls.accumulated_account = accumulated_account

    def _asset(self, cost=12000.0, salvage=0.0, life_months=12, acquisition_date="2026-01-01"):
        return self.env["bpro.plant.asset"].create(
            {
                "name": "Test Machine",
                "acquisition_date": acquisition_date,
                "acquisition_cost": cost,
                "salvage_value": salvage,
                "useful_life_months": life_months,
                "depreciation_expense_account_id": self.expense_account.id,
                "accumulated_depreciation_account_id": self.accumulated_account.id,
            }
        )

    def test_confirm_generates_one_line_per_month(self):
        asset = self._asset()
        asset.action_confirm()
        self.assertEqual(len(asset.depreciation_line_ids), 12)
        self.assertEqual(asset.state, "running")

    def test_schedule_sums_exactly_to_depreciable_amount(self):
        # 12500/7 doesn't divide evenly - checks the last line absorbs the
        # rounding remainder instead of the schedule drifting off by cents
        asset = self._asset(cost=12500.0, salvage=1000.0, life_months=7)
        asset.action_confirm()
        total = sum(asset.depreciation_line_ids.mapped("amount"))
        self.assertEqual(total, 11500.0)

    def test_confirm_is_idempotent(self):
        asset = self._asset()
        asset.action_confirm()
        asset.action_confirm()
        self.assertEqual(len(asset.depreciation_line_ids), 12)

    def test_cron_posts_only_due_lines(self):
        # far-future acquisition date so no line is due at whenever this
        # test actually runs
        asset = self._asset(acquisition_date="2099-01-01")
        asset.action_confirm()
        self.env["bpro.plant.asset.depreciation.line"]._bpro_cron_post_due_depreciation()
        posted = asset.depreciation_line_ids.filtered(lambda line: line.state == "posted")
        self.assertFalse(posted, "no line is due yet on a freshly confirmed asset")

    def test_posting_a_line_creates_a_balanced_journal_entry(self):
        asset = self._asset(cost=12000.0, life_months=12, acquisition_date="2026-01-01")
        asset.action_confirm()
        first_line = asset.depreciation_line_ids.sorted("period_date")[0]
        first_line.write({"period_date": "2026-01-02"})
        first_line._bpro_post()
        self.assertEqual(first_line.state, "posted")
        move = first_line.move_id
        self.assertEqual(move.state, "posted")
        self.assertEqual(sum(move.line_ids.mapped("debit")), 1000.0)
        self.assertEqual(sum(move.line_ids.mapped("credit")), 1000.0)
        self.assertEqual(asset.accumulated_depreciation, 1000.0)
        self.assertEqual(asset.book_value, 11000.0)

    def test_asset_fully_depreciated_once_all_lines_posted(self):
        asset = self._asset(cost=1000.0, life_months=2, acquisition_date="2026-01-01")
        asset.action_confirm()
        for line in asset.depreciation_line_ids:
            line.write({"period_date": "2026-01-02"})
            line._bpro_post()
        self.assertEqual(asset.state, "fully_depreciated")
        self.assertEqual(asset.book_value, 0.0)
