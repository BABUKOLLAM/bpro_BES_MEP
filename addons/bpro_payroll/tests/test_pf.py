from .common import PayrollTestCommon


class TestProvidentFund(PayrollTestCommon):
    """PF at the company's seeded default rates (12% employee, 12%
    employer split into 8.33% EPS + remainder EPF, 0.5% EDLI, 0.5% admin,
    15000 wage ceiling). ESI and TDS are switched off on every contract
    here so a PF assertion can't accidentally be passing (or failing)
    because of interference from an unrelated deduction."""

    def _pf_contract(self, ctc_annual, **kwargs):
        kwargs.setdefault("esi_applicable", False)
        kwargs.setdefault("tds_regime", False)
        return self._make_contract(ctc_annual, **kwargs)

    def test_pf_ee_is_capped_at_wage_ceiling_by_default(self):
        # Basic = 600000/12*50% = 25000, well above the 15000 ceiling -
        # 'capped' is the default pf_calculation_basis, so PF_WAGE should
        # be 15000, not the full 25000 Basic.
        contract = self._pf_contract(600000.0)
        payslip = self._make_payslip(contract, "2026-06-01", "2026-06-30")
        self.assertAlmostEqual(self._line_amount(payslip, "PF_EE"), 15000 * 0.12, places=2)

    def test_pf_ee_uses_full_basic_when_configured(self):
        contract = self._pf_contract(600000.0, pf_calculation_basis="full_basic")
        payslip = self._make_payslip(contract, "2026-06-01", "2026-06-30")
        self.assertAlmostEqual(self._line_amount(payslip, "PF_EE"), 25000 * 0.12, places=2)

    def test_eps_edli_admin_are_always_capped_regardless_of_basis(self):
        # The one rule this module is explicit about: EPS/EDLI/Admin are
        # always computed on wages capped at the ceiling by law, even
        # when the contract's own basis is 'full_basic' for EE/EPF.
        contract = self._pf_contract(600000.0, pf_calculation_basis="full_basic")
        payslip = self._make_payslip(contract, "2026-06-01", "2026-06-30")
        self.assertAlmostEqual(self._line_amount(payslip, "PF_EPS"), 15000 * 0.0833, places=2)
        self.assertAlmostEqual(self._line_amount(payslip, "PF_EDLI"), 15000 * 0.005, places=2)
        self.assertAlmostEqual(self._line_amount(payslip, "PF_ADMIN"), 15000 * 0.005, places=2)

    def test_employer_epf_share_is_employer_total_minus_eps(self):
        contract = self._pf_contract(600000.0)
        payslip = self._make_payslip(contract, "2026-06-01", "2026-06-30")
        employer_total = 15000 * 0.12
        eps = 15000 * 0.0833
        self.assertAlmostEqual(
            self._line_amount(payslip, "PF_EPF_ER"), employer_total - eps, places=2
        )

    def test_pf_applicable_false_zeroes_out_the_entire_pf_block(self):
        contract = self._pf_contract(600000.0, pf_applicable=False)
        payslip = self._make_payslip(contract, "2026-06-01", "2026-06-30")
        for code in ("PF_EE", "PF_EPS", "PF_EDLI", "PF_EPF_ER", "PF_ADMIN"):
            self.assertEqual(
                self._line_amount(payslip, code), 0.0,
                f"{code} should be 0 when pf_applicable is False",
            )

    def test_net_reflects_the_pf_employee_deduction(self):
        contract = self._pf_contract(600000.0)
        payslip = self._make_payslip(contract, "2026-06-01", "2026-06-30")
        gross = self._line_amount(payslip, "GROSS")
        pf_ee = self._line_amount(payslip, "PF_EE")
        net = self._line_amount(payslip, "NET")
        self.assertAlmostEqual(net, gross - pf_ee, places=2)
