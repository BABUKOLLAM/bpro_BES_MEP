from .common import PayrollTestCommon


class TestForm16(PayrollTestCommon):
    """Smoke coverage for the year-end aggregation, not a re-derivation
    of the monthly TDS engine's math (that's test_tds.py's job) - this
    exists to catch "Form 16 generation crashes" or "aggregates the
    wrong contract's payslips" rather than to re-verify tax slabs."""

    def test_generate_aggregates_confirmed_payslips_only(self):
        contract = self._make_contract(
            600000.0, pf_applicable=False, esi_applicable=False, tds_regime="new",
        )
        confirmed = self._make_payslip(contract, "2026-04-01", "2026-04-30")
        confirmed.action_payslip_done()
        draft = self._make_payslip(contract, "2026-05-01", "2026-05-31")
        # compute_sheet() advances a payslip to "verify", not "draft" - the
        # invariant Form16 relies on is "not done", not any specific
        # pre-confirmation state.
        self.assertNotEqual(draft.state, "done")

        form16 = self.env["bpro.tds.form16"].create({
            "contract_id": contract.id, "fy_start_year": 2026,
        })
        form16.action_generate()

        confirmed_gross = self._line_amount(confirmed, "GROSS")
        self.assertAlmostEqual(form16.gross_salary, confirmed_gross, places=2)
        self.assertGreater(form16.generated_date and 1 or 0, 0)

    def test_regenerating_after_a_second_confirmed_payslip_updates_the_total(self):
        contract = self._make_contract(
            600000.0, pf_applicable=False, esi_applicable=False, tds_regime="new",
        )
        first = self._make_payslip(contract, "2026-04-01", "2026-04-30")
        first.action_payslip_done()

        form16 = self.env["bpro.tds.form16"].create({
            "contract_id": contract.id, "fy_start_year": 2026,
        })
        form16.action_generate()
        after_one = form16.gross_salary

        second = self._make_payslip(contract, "2026-05-01", "2026-05-31")
        second.action_payslip_done()
        form16.action_generate()

        self.assertAlmostEqual(
            form16.gross_salary,
            after_one + self._line_amount(second, "GROSS"),
            places=2,
        )

    def test_balance_payable_is_liability_minus_withheld(self):
        contract = self._make_contract(
            600000.0, pf_applicable=False, esi_applicable=False, tds_regime="new",
        )
        payslip = self._make_payslip(contract, "2026-04-01", "2026-04-30")
        payslip.action_payslip_done()

        form16 = self.env["bpro.tds.form16"].create({
            "contract_id": contract.id, "fy_start_year": 2026,
        })
        form16.action_generate()
        self.assertAlmostEqual(
            form16.balance_payable,
            form16.total_tax_payable - form16.tds_deducted,
            places=2,
        )
