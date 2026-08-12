from datetime import date

from odoo import fields, models
from odoo.exceptions import UserError


class BproTdsForm16(models.Model):
    """Aggregates ACTUAL confirmed-payslip figures for the full financial
    year, rather than projecting like the monthly TDS rule does - at
    year-end the real numbers exist, no need to project.

    Deliberately does NOT deduct Professional Tax under section 16(iii),
    a real Old Regime deduction. This mirrors the R3.6a/b monthly TDS
    engine, which also omits it - kept consistent on purpose: applying a
    deduction here that was never applied during the year's monthly
    withholding would make this document disagree with what was actually
    withheld, which is worse than a shared, documented gap.
    """

    _name = "bpro.tds.form16"
    _description = "Form 16 Part B (computed salary/tax breakdown)"
    _order = "fy_start_year desc"

    contract_id = fields.Many2one("hr.contract", required=True, ondelete="cascade")
    employee_id = fields.Many2one(
        related="contract_id.employee_id", store=True, string="Employee"
    )
    company_id = fields.Many2one(
        related="contract_id.company_id", store=True
    )
    fy_start_year = fields.Integer(
        required=True,
        help="FY2026-27 (1 Apr 2026 - 31 Mar 2027) is 2026.",
    )
    regime = fields.Selection(
        [("new", "New Regime"), ("old", "Old Regime")],
        readonly=True,
        help="Snapshot of contract.tds_regime at generation time.",
    )
    gross_salary = fields.Float(readonly=True, help="Actual GROSS paid, summed from confirmed payslips in the FY.")
    hra_exemption = fields.Float(readonly=True)
    standard_deduction = fields.Float(readonly=True)
    deduction_80c = fields.Float(readonly=True)
    deduction_80d = fields.Float(readonly=True)
    taxable_income = fields.Float(readonly=True)
    tax_before_rebate = fields.Float(readonly=True)
    rebate_87a = fields.Float(readonly=True)
    tax_after_rebate = fields.Float(readonly=True)
    cess = fields.Float(readonly=True)
    total_tax_payable = fields.Float(readonly=True, help="Full-year tax liability computed from actual paid salary.")
    tds_deducted = fields.Float(readonly=True, help="Actual TDS withheld, summed from confirmed payslips in the FY.")
    balance_payable = fields.Float(
        readonly=True,
        help="total_tax_payable - tds_deducted. Positive = shortfall "
        "(employee owes more at self-assessment/ITR filing); negative = "
        "over-withheld (refund due via ITR).",
    )
    generated_date = fields.Date(readonly=True)

    _sql_constraints = [
        (
            "contract_fy_unique",
            "unique(contract_id, fy_start_year)",
            "Only one Form 16 per contract per financial year.",
        ),
    ]

    def _sum_code(self, contract, code, date_from, date_to):
        lines = self.env["hr.payslip.line"].search([
            ("slip_id.contract_id", "=", contract.id),
            ("slip_id.state", "=", "done"),
            ("slip_id.date_from", ">=", date_from),
            ("slip_id.date_to", "<=", date_to),
            ("code", "=", code),
        ])
        return sum((-l.total if l.slip_id.credit_note else l.total) for l in lines)

    def action_generate(self):
        for rec in self:
            contract = rec.contract_id
            if not contract.tds_regime:
                raise UserError("Contract has no TDS regime set - nothing to generate.")

            fy_start = date(rec.fy_start_year, 4, 1)
            fy_end = date(rec.fy_start_year + 1, 3, 31)

            gross = rec._sum_code(contract, "GROSS", fy_start, fy_end)
            basic = rec._sum_code(contract, "BASIC", fy_start, fy_end)
            hra = rec._sum_code(contract, "HRA", fy_start, fy_end)
            tds_deducted = rec._sum_code(contract, "TDS", fy_start, fy_end)

            regime = contract.tds_regime
            config = self.env["bpro.tds.regime.config"].search([
                ("regime", "=", regime),
                ("fy_start_year", "=", rec.fy_start_year),
            ], limit=1)
            if not config:
                raise UserError(
                    f"No TDS regime config found for {regime} regime, "
                    f"FY starting {rec.fy_start_year}."
                )

            hra_exemption = 0.0
            deduction_80c = 0.0
            deduction_80d = 0.0
            declaration = False
            if regime == "old":
                declaration = self.env["bpro.tds.declaration"].search([
                    ("contract_id", "=", contract.id),
                    ("fy_start_year", "=", rec.fy_start_year),
                    ("state", "=", "approved"),
                ], limit=1)
            if declaration:
                annual_rent = declaration.monthly_rent * 12.0
                hra_ceiling_pct = 0.50 if contract.hra_percent >= 50 else 0.40
                hra_exemption = max(0.0, min(
                    hra,
                    annual_rent - 0.10 * basic,
                    hra_ceiling_pct * basic,
                ))
                deduction_80c = min(declaration.declared_80c, 150000.0)
                deduction_80d = min(declaration.declared_80d, 25000.0)

            taxable_income = max(
                0.0,
                gross - hra_exemption - config.standard_deduction
                - deduction_80c - deduction_80d,
            )

            tax = 0.0
            for slab in config.slab_line_ids.sorted("lower_bound"):
                if taxable_income <= slab.lower_bound:
                    continue
                band_top = slab.upper_bound if slab.upper_bound else taxable_income
                band_amount = min(taxable_income, band_top) - slab.lower_bound
                if band_amount > 0:
                    tax += band_amount * (slab.rate / 100.0)

            rebate = 0.0
            if taxable_income <= config.rebate_income_threshold:
                rebate = min(tax, config.rebate_max_amount)
            tax_after_rebate = tax - rebate
            cess = tax_after_rebate * (config.cess_rate / 100.0)
            total_tax = tax_after_rebate + cess

            rec.write({
                "regime": regime,
                "gross_salary": gross,
                "hra_exemption": hra_exemption,
                "standard_deduction": config.standard_deduction,
                "deduction_80c": deduction_80c,
                "deduction_80d": deduction_80d,
                "taxable_income": taxable_income,
                "tax_before_rebate": tax,
                "rebate_87a": rebate,
                "tax_after_rebate": tax_after_rebate,
                "cess": cess,
                "total_tax_payable": total_tax,
                "tds_deducted": tds_deducted,
                "balance_payable": total_tax - tds_deducted,
                "generated_date": fields.Date.context_today(rec),
            })
