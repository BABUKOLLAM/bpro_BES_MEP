from datetime import date

from odoo.tests.common import TransactionCase


class PayrollTestCommon(TransactionCase):
    """Shared fixture for the payroll test suite: one company (statutory
    rates left at their seeded defaults - PF/ESI thresholds and rates,
    since those defaults ARE what production runs on until someone edits
    them), one employee, and helpers to build a contract + a computed
    payslip against the India CTC structure without repeating the same
    ten-line setup in every test file."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.env["account.chart.template"].try_loading(
            "generic_coa", cls.company, install_demo=False
        )
        cls.structure = cls.env.ref("bpro_payroll.structure_india_ctc")
        cls.employee = cls.env["hr.employee"].create({
            "name": "Payroll Test Employee", "company_id": cls.company.id,
        })

        # The four flexible-benefit templates (LTA/MEAL/CONV/SALW) all
        # have lower_bound=0.0 (see hr_contract_advantage_template_data.
        # xml) - pinning every contract's advantages to 0 keeps GROSS
        # fully predictable (= BASIC + HRA, no FBP contribution) without
        # asserting anything about the flexible-benefit mechanism itself,
        # which is OCA's, not this module's, to verify.
        cls.advantage_templates = cls.env["hr.contract.advantage.template"].search(
            [("code", "in", ["LTA", "MEAL", "CONV", "SALW"])]
        )

    def _make_contract(self, ctc_annual, **kwargs):
        # hr.contract enforces one non-draft/cancelled contract per employee
        # at a time; tests that build multiple contracts for the shared
        # fixture employee (e.g. to compare two CTCs) need the previous one
        # cancelled first.
        self.employee.contract_ids.filtered(
            lambda c: c.state not in ("cancel",)
        ).write({"state": "cancel"})
        vals = {
            "name": f"Payroll Test Contract {ctc_annual}",
            "employee_id": self.employee.id,
            "company_id": self.company.id,
            "struct_id": self.structure.id,
            "date_start": date(2026, 4, 1),
            "wage": 0.0,
            "ctc_annual": ctc_annual,
            "state": "open",
        }
        vals.update(kwargs)
        contract = self.env["hr.contract"].create(vals)
        contract.advantages_ids = [
            (0, 0, {"advantage_template_id": tmpl.id, "amount": 0.0})
            for tmpl in self.advantage_templates
        ]
        self.employee.contract_id = contract
        return contract

    def _make_payslip(self, contract, date_from, date_to):
        payslip = self.env["hr.payslip"].create({
            "employee_id": self.employee.id,
            "contract_id": contract.id,
            "date_from": date_from,
            "date_to": date_to,
        })
        payslip.onchange_employee()
        payslip.compute_sheet()
        return payslip

    @staticmethod
    def _line_amount(payslip, code):
        line = payslip.line_ids.filtered(lambda line_rec: line_rec.code == code)
        return sum(line.mapped("total")) if line else 0.0
