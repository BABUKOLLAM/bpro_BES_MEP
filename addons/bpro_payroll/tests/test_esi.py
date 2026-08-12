from .common import PayrollTestCommon


class TestEsi(PayrollTestCommon):
    """ESI is a pure threshold test on GROSS (not Basic, unlike PF) -
    either wages are at or below the company's esi_wage_threshold and
    ESI applies in full, or they aren't and it's zero. No capping/basis
    choice the way PF has. PF and TDS are switched off on every contract
    here to isolate ESI."""

    def _esi_contract(self, ctc_annual, **kwargs):
        kwargs.setdefault("pf_applicable", False)
        kwargs.setdefault("tds_regime", False)
        return self._make_contract(ctc_annual, **kwargs)

    def test_esi_applies_when_gross_is_at_or_below_threshold(self):
        # ctc_annual=200000 -> monthly 16666.67, Basic 8333.33 (50%),
        # HRA 3333.33 (40% of Basic), Gross 11666.67 - comfortably under
        # the default 21000 threshold.
        contract = self._esi_contract(200000.0)
        payslip = self._make_payslip(contract, "2026-06-01", "2026-06-30")
        gross = self._line_amount(payslip, "GROSS")
        self.assertLess(gross, 21000.0)
        self.assertAlmostEqual(
            self._line_amount(payslip, "ESI_EE"), gross * 0.0075, places=2
        )
        self.assertAlmostEqual(
            self._line_amount(payslip, "ESI_ER"), gross * 0.0325, places=2
        )

    def test_esi_does_not_apply_when_gross_exceeds_threshold(self):
        # ctc_annual=600000 -> Gross 35000, above the 21000 threshold.
        contract = self._esi_contract(600000.0)
        payslip = self._make_payslip(contract, "2026-06-01", "2026-06-30")
        self.assertGreater(self._line_amount(payslip, "GROSS"), 21000.0)
        self.assertEqual(self._line_amount(payslip, "ESI_EE"), 0.0)
        self.assertEqual(self._line_amount(payslip, "ESI_ER"), 0.0)

    def test_esi_applicable_false_overrides_a_below_threshold_gross(self):
        # Even though this contract's Gross would otherwise qualify,
        # esi_applicable=False must still zero it out - an HR-set
        # exclusion, not just a wage check.
        contract = self._esi_contract(200000.0, esi_applicable=False)
        payslip = self._make_payslip(contract, "2026-06-01", "2026-06-30")
        self.assertLess(self._line_amount(payslip, "GROSS"), 21000.0)
        self.assertEqual(self._line_amount(payslip, "ESI_EE"), 0.0)
        self.assertEqual(self._line_amount(payslip, "ESI_ER"), 0.0)

    def test_esi_re_checks_the_threshold_every_payslip(self):
        # Same contract, two different CTCs across two months - confirms
        # the rule reacts to whatever Gross actually is that month, not a
        # value cached from an earlier payslip.
        contract = self._esi_contract(200000.0)
        below = self._make_payslip(contract, "2026-06-01", "2026-06-30")
        self.assertGreater(self._line_amount(below, "ESI_EE"), 0.0)

        contract.write({"ctc_annual": 600000.0})
        above = self._make_payslip(contract, "2026-07-01", "2026-07-31")
        self.assertEqual(self._line_amount(above, "ESI_EE"), 0.0)
