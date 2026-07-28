from datetime import date

from .common import FinanceTestCommon


class TestFinancialReports(FinanceTestCommon):
    """A single hand-built scenario spanning a 'setup' period (establishing
    opening balances) and a 'test' period (2026-04-01 to 2026-04-30), with
    every expected figure below independently computed by hand from the
    posted entries - not derived from the code under test."""

    def setUp(self):
        super().setUp()

        def acc(name, code, account_type):
            return self.env["account.account"].create(
                {
                    "name": name,
                    "code": code,
                    "account_type": account_type,
                    "company_ids": [(6, 0, [self.company.id])],
                }
            )

        self.a_cash = acc("Test Cash", "TCASH1", "asset_cash")
        self.a_fixed = acc("Test Fixed Asset", "TFIX1", "asset_fixed")
        self.a_receivable = acc("Test Receivable", "TRECV1", "asset_receivable")
        self.a_other_cur_asset = acc("Test Inventory", "TINV1", "asset_current")
        self.a_payable = acc("Test Payable", "TPAY1", "liability_payable")
        self.a_other_cur_liab = acc("Test Accrued Expense", "TACCR1", "liability_current")
        self.a_noncurrent_liab = acc("Test Long-term Loan", "TLOAN1", "liability_non_current")
        self.a_equity = acc("Test Capital", "TCAP1", "equity")
        self.a_income = acc("Test Sales", "TSALE1", "income")
        self.a_expense = acc("Test Expense", "TEXP1", "expense")
        self.a_depreciation = acc("Test Depreciation", "TDEP1", "expense_depreciation")

        def post(entry_date, debit_account, credit_account, amount):
            move = self.env["account.move"].create(
                {
                    "move_type": "entry",
                    "date": entry_date,
                    "line_ids": [
                        (0, 0, {"account_id": debit_account.id, "debit": amount, "credit": 0.0}),
                        (0, 0, {"account_id": credit_account.id, "debit": 0.0, "credit": amount}),
                    ],
                }
            )
            move.action_post()
            return move

        # Setup period (establishes opening balances as of 2026-03-31):
        # capital introduced, then a fixed asset purchased with part of it.
        post("2026-01-15", self.a_cash, self.a_equity, 10000.0)
        post("2026-01-20", self.a_fixed, self.a_cash, 5000.0)

        # Test period 2026-04-01 - 2026-04-30.
        post("2026-04-05", self.a_receivable, self.a_income, 2000.0)  # credit sale
        post("2026-04-10", self.a_cash, self.a_receivable, 1200.0)  # partial collection
        post("2026-04-12", self.a_other_cur_asset, self.a_payable, 600.0)  # inventory on credit
        post("2026-04-15", self.a_expense, self.a_payable, 900.0)  # expense on credit
        post("2026-04-20", self.a_payable, self.a_cash, 500.0)  # pay down payable
        post("2026-04-22", self.a_depreciation, self.a_fixed, 200.0)  # depreciation charge
        post("2026-04-25", self.a_cash, self.a_noncurrent_liab, 1000.0)  # loan raised
        post("2026-04-28", self.a_cash, self.a_equity, 300.0)  # additional capital
        post("2026-04-29", self.a_expense, self.a_other_cur_liab, 150.0)  # accrued expense

        self.date_from = date(2026, 4, 1)
        self.date_to = date(2026, 4, 30)

    def test_trial_balance_debit_equals_credit_and_closing_matches_movement(self):
        data = self.env["bpro.trial.balance.wizard"]._get_trial_balance_data(
            self.company, self.date_from, self.date_to
        )
        by_account = {row["account_id"]: row for row in data}

        total_closing_debit = sum(r["closing_debit"] for r in data)
        total_closing_credit = sum(r["closing_credit"] for r in data)
        self.assertAlmostEqual(total_closing_debit, total_closing_credit, places=2)

        receivable_row = by_account[self.a_receivable.id]
        self.assertEqual(receivable_row["opening_debit"], 0.0)
        self.assertEqual(receivable_row["debit"], 2000.0)
        self.assertEqual(receivable_row["credit"], 1200.0)
        self.assertEqual(receivable_row["closing_debit"], 800.0)

        cash_row = by_account[self.a_cash.id]
        self.assertEqual(cash_row["opening_debit"], 5000.0)
        self.assertEqual(cash_row["closing_debit"], 7000.0)

        equity_row = by_account[self.a_equity.id]
        self.assertEqual(equity_row["opening_credit"], 10000.0)
        self.assertEqual(equity_row["closing_credit"], 10300.0)

    def test_balance_sheet_balances_to_zero(self):
        data = self.env["bpro.balance.sheet.wizard"]._get_balance_sheet_data(
            self.company, self.date_to
        )
        self.assertAlmostEqual(data["total_assets"], 13200.0, places=2)
        self.assertAlmostEqual(data["total_liabilities_equity"], 13200.0, places=2)
        self.assertAlmostEqual(
            data["total_assets"] - data["total_liabilities_equity"], 0.0, places=2
        )

    def test_profit_and_loss_net_profit(self):
        data = self.env["bpro.profit.loss.wizard"]._get_pl_data(
            self.company, self.date_from, self.date_to
        )
        self.assertAlmostEqual(data["total_income"], 2000.0, places=2)
        self.assertAlmostEqual(data["total_expense"], 1250.0, places=2)
        self.assertAlmostEqual(data["net_profit"], 750.0, places=2)

    def test_cash_flow_reconciles_to_actual_cash_movement(self):
        data = self.env["bpro.cash.flow.wizard"]._get_cash_flow_data(
            self.company, self.date_from, self.date_to
        )
        self.assertAlmostEqual(data["actual_cash_movement"], 2000.0, places=2)
        self.assertAlmostEqual(data["net_increase_in_cash"], 2000.0, places=2)
        self.assertAlmostEqual(
            data["net_increase_in_cash"] - data["actual_cash_movement"], 0.0, places=2
        )

    def test_fund_flow_reconciles_to_working_capital_schedule(self):
        data = self.env["bpro.fund.flow.wizard"]._get_fund_flow_data(
            self.company, self.date_from, self.date_to
        )
        self.assertAlmostEqual(data["net_increase_in_working_capital"], 2250.0, places=2)
        self.assertAlmostEqual(data["working_capital_schedule_check"], 2250.0, places=2)
        self.assertAlmostEqual(
            data["net_increase_in_working_capital"] - data["working_capital_schedule_check"],
            0.0,
            places=2,
        )

    def test_cash_flow_reconciliation_holds_with_real_capex_not_just_depreciation(self):
        # Add a genuine fixed-asset purchase in the same period, on top of
        # the existing depreciation entry, to prove the gross-up logic
        # still reconciles when both effects are present simultaneously.
        move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": "2026-04-27",
                "line_ids": [
                    (0, 0, {"account_id": self.a_fixed.id, "debit": 1000.0, "credit": 0.0}),
                    (0, 0, {"account_id": self.a_cash.id, "debit": 0.0, "credit": 1000.0}),
                ],
            }
        )
        move.action_post()

        cf_data = self.env["bpro.cash.flow.wizard"]._get_cash_flow_data(
            self.company, self.date_from, self.date_to
        )
        self.assertAlmostEqual(
            cf_data["net_increase_in_cash"] - cf_data["actual_cash_movement"], 0.0, places=2
        )

        ff_data = self.env["bpro.fund.flow.wizard"]._get_fund_flow_data(
            self.company, self.date_from, self.date_to
        )
        self.assertAlmostEqual(
            ff_data["net_increase_in_working_capital"]
            - ff_data["working_capital_schedule_check"],
            0.0,
            places=2,
        )
