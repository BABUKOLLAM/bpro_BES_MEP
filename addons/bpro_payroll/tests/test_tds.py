from .common import PayrollTestCommon


class TestTds(PayrollTestCommon):
    """The TDS engine's projected-annual method is genuinely complex
    (accumulated actual + projected remainder, progressive slabs, 87A
    rebate, cess) - re-deriving its exact output by hand for a
    multi-bracket income risks the test asserting a wrong number I
    transcribed rather than catching a real bug. Where the arithmetic is
    simple enough to be sure of (nil slab, the 87A rebate boundary),
    these assert exact figures; for genuinely higher incomes they assert
    direction (>0) and that regime/income actually change the result -
    still enough to catch "TDS silently always returns 0" or "regime
    setting is ignored", which are the realistic risks here.

    All payslips are dated in April (the FY's first month) so the
    projected-annual calculation simplifies to this month's Gross x 12 -
    no prior confirmed payslips exist yet to accumulate.
    """

    def _tds_contract(self, ctc_annual, **kwargs):
        kwargs.setdefault("pf_applicable", False)
        kwargs.setdefault("esi_applicable", False)
        kwargs.setdefault("tds_regime", "new")
        return self._make_contract(ctc_annual, **kwargs)

    def test_no_tds_when_projected_income_is_entirely_within_the_nil_slab(self):
        # ctc_annual=600000 -> Gross 35000/month -> projected annual
        # 420000, minus the new regime's 75000 standard deduction =
        # 345000 taxable, entirely within the new regime's 0-400000 nil
        # band.
        contract = self._tds_contract(600000.0)
        payslip = self._make_payslip(contract, "2026-04-01", "2026-04-30")
        self.assertEqual(self._line_amount(payslip, "TDS"), 0.0)

    def test_87a_rebate_zeroes_a_moderate_tax_liability(self):
        # ctc_annual=1500000 -> Gross 87500/month -> projected annual
        # 1050000, minus std deduction 75000 = 975000 taxable (9.75L).
        # Tax before rebate: 400000 nil, next 575000 at 5% = 28750.
        # That's under the 60000 87A rebate (available since taxable
        # income <= 12L), so net TDS should be 0 - not because the slab
        # is nil, but because the rebate cancels it. A different code
        # path than the previous test; worth its own case.
        contract = self._tds_contract(1500000.0)
        payslip = self._make_payslip(contract, "2026-04-01", "2026-04-30")
        self.assertEqual(self._line_amount(payslip, "TDS"), 0.0)

    def test_tds_is_positive_once_income_exceeds_rebate_eligibility(self):
        # ctc_annual=2500000 -> taxable well above the 12L rebate
        # ceiling - TDS must be strictly positive.
        contract = self._tds_contract(2500000.0)
        payslip = self._make_payslip(contract, "2026-04-01", "2026-04-30")
        self.assertGreater(self._line_amount(payslip, "TDS"), 0.0)

    def test_higher_income_means_higher_tds(self):
        lower = self._make_payslip(
            self._tds_contract(2500000.0), "2026-04-01", "2026-04-30"
        )
        higher = self._make_payslip(
            self._tds_contract(4000000.0), "2026-04-01", "2026-04-30"
        )
        self.assertGreater(
            self._line_amount(higher, "TDS"), self._line_amount(lower, "TDS")
        )

    def test_old_regime_gives_a_different_figure_than_new_regime(self):
        # Same CTC, different declared regime - if this module ever
        # collapsed to always using one regime's slabs regardless of
        # tds_regime, this would silently pass with equal figures.
        new_regime = self._make_payslip(
            self._tds_contract(2500000.0, tds_regime="new"), "2026-04-01", "2026-04-30"
        )
        old_regime = self._make_payslip(
            self._tds_contract(2500000.0, tds_regime="old"), "2026-04-01", "2026-04-30"
        )
        self.assertGreater(self._line_amount(old_regime, "TDS"), 0.0)
        self.assertNotAlmostEqual(
            self._line_amount(new_regime, "TDS"),
            self._line_amount(old_regime, "TDS"),
            places=2,
        )

    def test_no_regime_declared_means_no_tds(self):
        contract = self._tds_contract(2500000.0, tds_regime=False)
        payslip = self._make_payslip(contract, "2026-04-01", "2026-04-30")
        self.assertEqual(self._line_amount(payslip, "TDS"), 0.0)
