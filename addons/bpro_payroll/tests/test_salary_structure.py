from .common import PayrollTestCommon


class TestSalaryStructure(PayrollTestCommon):
    """R3.1 foundation: Basic/HRA/Gross derived from CTC and company
    policy percentages. Deliberately does not assert NET here - by the
    time every release (PF/ESI/PT/LWF/TDS) is combined into one
    structure, NET depends on all of them, and entangling that with the
    foundation math would make a break in, say, the TDS engine look like
    a Basic/HRA regression. Each deduction gets its own isolated test
    file; this one only owns the Gross side."""

    def test_basic_is_ctc_over_12_times_basic_percent(self):
        contract = self._make_contract(600000.0, tds_regime=False)
        payslip = self._make_payslip(contract, "2026-06-01", "2026-06-30")
        # 600000 / 12 * 50% = 25000
        self.assertAlmostEqual(self._line_amount(payslip, "BASIC"), 25000.0, places=2)

    def test_hra_is_basic_times_hra_percent(self):
        contract = self._make_contract(600000.0, tds_regime=False)
        payslip = self._make_payslip(contract, "2026-06-01", "2026-06-30")
        # 25000 * 40% = 10000
        self.assertAlmostEqual(self._line_amount(payslip, "HRA"), 10000.0, places=2)

    def test_gross_is_basic_plus_hra_plus_zeroed_fbp(self):
        contract = self._make_contract(600000.0, tds_regime=False)
        payslip = self._make_payslip(contract, "2026-06-01", "2026-06-30")
        self.assertAlmostEqual(self._line_amount(payslip, "GROSS"), 35000.0, places=2)

    def test_a_different_basic_percent_changes_both_basic_and_hra(self):
        # Confirms the policy fields are actually read, not hardcoded -
        # basic_percent=60 with the same CTC should move both Basic (more
        # of the CTC) and HRA (computed off the new, larger Basic).
        contract = self._make_contract(
            600000.0, basic_percent=60.0, hra_percent=40.0, tds_regime=False
        )
        payslip = self._make_payslip(contract, "2026-06-01", "2026-06-30")
        self.assertAlmostEqual(self._line_amount(payslip, "BASIC"), 30000.0, places=2)
        self.assertAlmostEqual(self._line_amount(payslip, "HRA"), 12000.0, places=2)
