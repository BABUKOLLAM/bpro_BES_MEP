from .common import PayrollTestCommon


class TestProfessionalTaxAndLwf(PayrollTestCommon):
    """Kerala's real seeded PT and LWF config (the same data verified
    for ME Polymers) - both are half-yearly and only charge in specific
    months, which is the part actually worth testing here: that the
    rule doesn't just look up a slab and always apply it, but gates on
    payslip.date_to.month matching the config's charge month."""

    def _kerala_contract(self, ctc_annual, **kwargs):
        kwargs.setdefault("pf_applicable", False)
        kwargs.setdefault("esi_applicable", False)
        kwargs.setdefault("tds_regime", False)
        kwargs["pt_state_id"] = self.env.ref("bpro_payroll.pt_config_kerala").id
        kwargs["lwf_state_id"] = self.env.ref("bpro_payroll.lwf_config_kerala").id
        return self._make_contract(ctc_annual, **kwargs)

    def test_pt_charges_in_the_configured_month_only(self):
        # ctc_annual=600000 -> Gross 35000, in Kerala's 30000-44999 band
        # (Rs.300). Kerala's H1 charge month is August (8).
        contract = self._kerala_contract(600000.0)
        off_month = self._make_payslip(contract, "2026-06-01", "2026-06-30")
        self.assertEqual(self._line_amount(off_month, "PT"), 0.0)

        charge_month = self._make_payslip(contract, "2026-08-01", "2026-08-31")
        self.assertAlmostEqual(self._line_amount(charge_month, "PT"), 300.0, places=2)

    def test_pt_has_no_slab_below_the_nil_band(self):
        # ctc_annual=100000 -> monthly 8333.33, Basic 4166.67, HRA
        # 1666.67, Gross 5833.33 - below Kerala's 11999 nil ceiling, so
        # PT is 0 even in the charge month.
        contract = self._kerala_contract(100000.0)
        payslip = self._make_payslip(contract, "2026-08-01", "2026-08-31")
        self.assertLess(self._line_amount(payslip, "GROSS"), 12000.0)
        self.assertEqual(self._line_amount(payslip, "PT"), 0.0)

    def test_lwf_charges_only_in_june_and_december(self):
        # Kerala LWF (1975 Act): Rs.45 employee + Rs.45 employer,
        # half-yearly, charge months June (6) and December (12).
        contract = self._kerala_contract(600000.0)

        off_month = self._make_payslip(contract, "2026-08-01", "2026-08-31")
        self.assertEqual(self._line_amount(off_month, "LWF_EE"), 0.0)
        self.assertEqual(self._line_amount(off_month, "LWF_ER"), 0.0)

        h1_charge = self._make_payslip(contract, "2026-06-01", "2026-06-30")
        self.assertAlmostEqual(self._line_amount(h1_charge, "LWF_EE"), 45.0, places=2)
        self.assertAlmostEqual(self._line_amount(h1_charge, "LWF_ER"), 45.0, places=2)

        h2_charge = self._make_payslip(contract, "2026-12-01", "2026-12-31")
        self.assertAlmostEqual(self._line_amount(h2_charge, "LWF_EE"), 45.0, places=2)
        self.assertAlmostEqual(self._line_amount(h2_charge, "LWF_ER"), 45.0, places=2)

    def test_no_state_configured_means_no_pt_or_lwf(self):
        contract = self._make_contract(
            600000.0, pf_applicable=False, esi_applicable=False, tds_regime=False,
        )
        payslip = self._make_payslip(contract, "2026-08-01", "2026-08-31")
        self.assertEqual(self._line_amount(payslip, "PT"), 0.0)
        self.assertEqual(self._line_amount(payslip, "LWF_EE"), 0.0)
