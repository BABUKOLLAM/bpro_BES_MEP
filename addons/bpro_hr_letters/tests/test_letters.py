from datetime import date, timedelta

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestHrLetters(TransactionCase):
    """R6.4 - letters snapshot the contract at creation, get sequenced
    references, and exits auto-generate the relieving letter."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.job = cls.env["hr.job"].create({"name": "Letter Test Role"})
        cls.employee = cls.env["hr.employee"].create({
            "name": "Letter Test Employee", "company_id": cls.company.id,
            "job_id": cls.job.id,
        })
        cls.env["hr.contract"].create({
            "name": "Letter contract", "employee_id": cls.employee.id,
            "wage": 20000, "ctc_annual": 240000.0,
            "basic_percent": 50.0, "hra_percent": 40.0,
            "date_start": date(2024, 1, 1), "state": "open",
        })

    def test_salary_certificate_snapshots_contract(self):
        letter = self.env["bpro.hr.letter"].create({
            "employee_id": self.employee.id,
            "letter_type": "salary_certificate",
        })
        self.assertTrue(letter.reference.startswith("LTR"))
        self.assertEqual(letter.designation, "Letter Test Role")
        self.assertEqual(letter.ctc_annual, 240000.0)
        self.assertAlmostEqual(letter.monthly_gross, 14000.0, places=2)
        self.assertEqual(letter.service_from, date(2024, 1, 1))

    def test_references_are_sequential_and_unique(self):
        first = self.env["bpro.hr.letter"].create({
            "employee_id": self.employee.id, "letter_type": "address_proof",
        })
        second = self.env["bpro.hr.letter"].create({
            "employee_id": self.employee.id, "letter_type": "address_proof",
        })
        self.assertNotEqual(first.reference, second.reference)

    def test_increment_requires_revised_ctc(self):
        letter = self.env["bpro.hr.letter"].create({
            "employee_id": self.employee.id, "letter_type": "increment",
        })
        with self.assertRaises(UserError):
            letter.action_print()
        letter.revised_ctc = 300000.0
        letter.action_print()

    def test_exit_close_creates_relieving_letter(self):
        user = self.env["res.users"].create({
            "name": "Letter Exit User", "login": "letter_exit",
            "email": "letter_exit@example.com",
        })
        employee = self.env["hr.employee"].create({
            "name": "Letter Exit Employee", "company_id": self.company.id,
            "user_id": user.id, "job_id": self.job.id,
        })
        self.env["hr.contract"].create({
            "name": "Letter exit contract", "employee_id": employee.id,
            "wage": 20000, "ctc_annual": 240000.0,
            "basic_percent": 50.0, "hra_percent": 40.0,
            "date_start": date.today() - timedelta(days=6 * 365), "state": "open",
        })
        exit_request = self.env["bpro.exit.request"].create({
            "employee_id": employee.id,
        })
        exit_request.action_submit()
        exit_request.action_accept()
        for line in exit_request.clearance_line_ids:
            line.action_mark_done()
        exit_request.action_settle()
        exit_request.action_close()
        letter = exit_request.relieving_letter_id
        self.assertTrue(letter)
        self.assertEqual(letter.letter_type, "experience")
        self.assertEqual(letter.service_to, exit_request.last_working_day)
        self.assertEqual(letter.employee_id, employee)
