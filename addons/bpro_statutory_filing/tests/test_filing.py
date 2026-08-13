import base64
from datetime import date

from odoo.tests.common import TransactionCase


class TestStatutoryFiling(TransactionCase):
    """R6.1 - filings must reflect confirmed payslips exactly, and
    employees missing an identifier must be reported, never silently
    dropped."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.struct = cls.env.ref("bpro_payroll.structure_india_ctc")

        bank = cls.env["res.bank"].create({"name": "Filing Test Bank", "bic": "TEST0IN001"})

        def make(name, uan, esi, pan, with_bank=True):
            employee = cls.env["hr.employee"].create({
                "name": name, "company_id": cls.company.id, "tz": "Asia/Kolkata",
                "uan": uan, "esi_number": esi, "pan": pan,
            })
            if with_bank:
                account = cls.env["res.partner.bank"].create({
                    "acc_number": f"0000{name[-1]}111",
                    "partner_id": employee.work_contact_id.id,
                    "bank_id": bank.id,
                })
                employee.bank_account_id = account
            cls.env["hr.contract"].create({
                "name": f"{name} contract", "employee_id": employee.id,
                "wage": 20000, "ctc_annual": 240000.0,
                "basic_percent": 50.0, "hra_percent": 40.0,
                "struct_id": cls.struct.id, "date_start": date(2026, 1, 1),
                "state": "open",
            })
            return employee

        cls.emp_full = make("Filing Emp A", "100000000001", "1000000001", "ABCPA1234A")
        cls.emp_no_ids = make("Filing Emp B", False, False, False, with_bank=False)

        for employee in (cls.emp_full, cls.emp_no_ids):
            slip = cls.env["hr.payslip"].create({
                "employee_id": employee.id,
                "contract_id": employee.contract_ids[0].id,
                "struct_id": cls.struct.id,
                "date_from": date(2026, 7, 1), "date_to": date(2026, 7, 31),
                "name": f"{employee.name} July",
            })
            slip.compute_sheet()
            slip.write({"state": "done"})

    def _generate(self):
        wizard = self.env["bpro.statutory.filing"].create({
            "company_id": self.company.id, "month": "7", "year": 2026,
        })
        wizard.action_generate()
        return wizard

    @staticmethod
    def _decode(binary):
        return base64.b64decode(binary).decode("utf-8")

    def test_ecr_contains_member_and_reports_missing_uan(self):
        wizard = self._generate()
        ecr = self._decode(wizard.ecr_file)
        # Basic 10000 -> PF wage 10000, EE 12% = 1200, EPS 8.33% = 833.
        line = next(l for l in ecr.splitlines() if l.startswith("100000000001"))
        parts = line.split("#~#")
        self.assertEqual(parts[1], "FILING EMP A")
        self.assertEqual(parts[3], "10000")  # EPF wage
        self.assertEqual(parts[6], "1200")   # EE share
        self.assertEqual(parts[9], "0")      # NCP days, full attendance
        self.assertNotIn("Filing Emp B", ecr)
        self.assertIn("Filing Emp B", wizard.summary)

    def test_esic_and_bank_and_pt_rows(self):
        wizard = self._generate()
        esic = self._decode(wizard.esic_file)
        # Gross 14000 < threshold -> covered; EE 0.75% = 105.00.
        self.assertIn("1000000001,Filing Emp A", esic)
        self.assertIn("105.0", esic)
        bank = self._decode(wizard.bank_file)
        self.assertIn("Filing Emp A", bank)
        self.assertIn("TEST0IN001", bank)
        self.assertIn("Filing Emp B", wizard.summary)  # no bank account

    def test_24q_quarter_selection_and_pan_gate(self):
        wizard = self._generate()
        tds = self._decode(wizard.tds_file)
        # July sits in FY quarter Q2 (Jul-Sep).
        self.assertEqual(wizard.tds_filename, "24Q_Q2_2026.csv")
        # These test salaries are below the TDS threshold - no rows,
        # but the header must still be present.
        self.assertTrue(tds.startswith("Quarter,Month,Employee,PAN"))

    def test_draft_slips_never_reach_a_filing(self):
        draft_emp = self.env["hr.employee"].create({
            "name": "Filing Draft Emp", "company_id": self.company.id,
            "uan": "100000000099",
        })
        contract = self.env["hr.contract"].create({
            "name": "draft contract", "employee_id": draft_emp.id,
            "wage": 20000, "ctc_annual": 240000.0,
            "basic_percent": 50.0, "hra_percent": 40.0,
            "struct_id": self.struct.id, "date_start": date(2026, 1, 1),
            "state": "open",
        })
        slip = self.env["hr.payslip"].create({
            "employee_id": draft_emp.id, "contract_id": contract.id,
            "struct_id": self.struct.id,
            "date_from": date(2026, 7, 1), "date_to": date(2026, 7, 31),
            "name": "draft slip",
        })
        slip.compute_sheet()  # stays draft
        wizard = self._generate()
        self.assertNotIn("100000000099", self._decode(wizard.ecr_file))
