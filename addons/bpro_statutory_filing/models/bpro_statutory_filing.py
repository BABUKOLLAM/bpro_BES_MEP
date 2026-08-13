import base64
import calendar
from datetime import date

from odoo import fields, models
from odoo.exceptions import UserError

MONTHS = [
    (str(i), name)
    for i, name in enumerate(
        ["January", "February", "March", "April", "May", "June", "July",
         "August", "September", "October", "November", "December"],
        start=1,
    )
]

# Indian financial-year quarters for Form 24Q: Q1 Apr-Jun ... Q4 Jan-Mar.
FY_QUARTERS = {
    "Q1": (4, 5, 6),
    "Q2": (7, 8, 9),
    "Q3": (10, 11, 12),
    "Q4": (1, 2, 3),
}


class BproStatutoryFiling(models.TransientModel):
    _name = "bpro.statutory.filing"
    _description = "Statutory Filing Generator"

    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    month = fields.Selection(MONTHS, required=True, default=lambda self: str(fields.Date.context_today(self).month))
    year = fields.Integer(required=True, default=lambda self: fields.Date.context_today(self).year)

    ecr_file = fields.Binary(readonly=True)
    ecr_filename = fields.Char(readonly=True)
    esic_file = fields.Binary(readonly=True)
    esic_filename = fields.Char(readonly=True)
    pt_file = fields.Binary(readonly=True)
    pt_filename = fields.Char(readonly=True)
    tds_file = fields.Binary(readonly=True)
    tds_filename = fields.Char(readonly=True)
    bank_file = fields.Binary(readonly=True)
    bank_filename = fields.Char(readonly=True)
    summary = fields.Text(readonly=True)

    def _period(self, month=None, year=None):
        month = month or int(self.month)
        year = year or self.year
        return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])

    def _done_payslips(self, month=None, year=None):
        """Only CONFIRMED payslips reach a filing - a draft is HR
        work-in-progress and must never be uploaded to a portal."""
        date_from, date_to = self._period(month, year)
        return self.env["hr.payslip"].search([
            ("company_id", "=", self.company_id.id),
            ("state", "=", "done"),
            ("date_from", ">=", date_from),
            ("date_to", "<=", date_to),
        ])

    @staticmethod
    def _lines(slip):
        return {line.code: line.total for line in slip.line_ids}

    def action_generate(self):
        self.ensure_one()
        slips = self._done_payslips()
        if not slips:
            raise UserError(
                "No confirmed payslips found for the selected month - "
                "confirm the payroll run first (drafts never reach a filing)."
            )
        notes = []
        period_tag = f"{self.year}{int(self.month):02d}"

        # --- EPFO ECR ---
        ecr_rows, skipped = [], []
        for slip in slips:
            lines = self._lines(slip)
            if not lines.get("PF_EE"):
                continue
            if not slip.employee_id.uan:
                skipped.append(slip.employee_id.name)
                continue
            ncp_days, _working = slip.bpro_lop_days(slip.employee_id, slip.contract_id)
            epf_wage = lines.get("PF_WAGE", 0)
            eps_wage = min(epf_wage, self.company_id.pf_wage_ceiling)
            ecr_rows.append("#~#".join(str(v) for v in [
                slip.employee_id.uan,
                slip.employee_id.name.upper(),
                round(lines.get("GROSS", 0)),
                round(epf_wage),
                round(eps_wage),
                round(eps_wage),  # EDLI wage: always ceiling-capped
                round(lines.get("PF_EE", 0)),
                round(lines.get("PF_EPS", 0)),
                round(lines.get("PF_EPF_ER", 0)),
                ncp_days,
                0,  # refund of advances
            ]))
        self.ecr_file = base64.b64encode("\n".join(ecr_rows).encode("utf-8"))
        self.ecr_filename = f"ECR_{period_tag}.txt"
        notes.append(f"ECR: {len(ecr_rows)} member(s)."
                     + (f" Skipped (no UAN): {', '.join(skipped)}" if skipped else ""))

        # --- ESIC contribution ---
        esic_rows, skipped = ["IP Number,IP Name,Days Worked,Total Wages,IP Contribution"], []
        for slip in slips:
            lines = self._lines(slip)
            if not lines.get("ESI_EE"):
                continue
            if not slip.employee_id.esi_number:
                skipped.append(slip.employee_id.name)
                continue
            ncp_days, working = slip.bpro_lop_days(slip.employee_id, slip.contract_id)
            esic_rows.append(",".join(str(v) for v in [
                slip.employee_id.esi_number,
                slip.employee_id.name,
                working - ncp_days,
                round(lines.get("GROSS", 0), 2),
                round(lines.get("ESI_EE", 0), 2),
            ]))
        self.esic_file = base64.b64encode("\n".join(esic_rows).encode("utf-8"))
        self.esic_filename = f"ESIC_{period_tag}.csv"
        notes.append(f"ESIC: {len(esic_rows) - 1} IP(s)."
                     + (f" Skipped (no IP number): {', '.join(skipped)}" if skipped else ""))

        # --- Professional Tax, grouped per state ---
        pt_rows = ["State,Employee,Gross,PT Deducted"]
        state_totals = {}
        for slip in slips:
            lines = self._lines(slip)
            pt = lines.get("PT", 0)
            state = slip.contract_id.pt_state_id.name or "No PT State"
            if not pt:
                continue
            pt_rows.append(f"{state},{slip.employee_id.name},{round(lines.get('GROSS', 0), 2)},{round(pt, 2)}")
            state_totals[state] = state_totals.get(state, 0.0) + pt
        for state in sorted(state_totals):
            pt_rows.append(f"{state},TOTAL,,{round(state_totals[state], 2)}")
        self.pt_file = base64.b64encode("\n".join(pt_rows).encode("utf-8"))
        self.pt_filename = f"PT_{period_tag}.csv"
        notes.append(f"PT: {len(state_totals)} state(s), total "
                     f"{round(sum(state_totals.values()), 2)}.")

        # --- Form 24Q data (the quarter containing the selected month) ---
        month = int(self.month)
        quarter = next(q for q, months in FY_QUARTERS.items() if month in months)
        tds_rows = ["Quarter,Month,Employee,PAN,TDS Deducted"]
        skipped = set()
        for q_month in FY_QUARTERS[quarter]:
            # Q4 spans the calendar-year boundary (Jan-Mar belong to the
            # FY that started the previous April).
            q_year = self.year
            for slip in self._done_payslips(month=q_month, year=q_year):
                lines = self._lines(slip)
                tds = lines.get("TDS", 0)
                if not tds:
                    continue
                if not slip.employee_id.pan:
                    skipped.add(slip.employee_id.name)
                    continue
                tds_rows.append(
                    f"{quarter},{q_month},{slip.employee_id.name},"
                    f"{slip.employee_id.pan},{round(tds, 2)}"
                )
        self.tds_file = base64.b64encode("\n".join(tds_rows).encode("utf-8"))
        self.tds_filename = f"24Q_{quarter}_{self.year}.csv"
        notes.append(f"24Q ({quarter}): {len(tds_rows) - 1} row(s)."
                     + (f" Skipped (no PAN): {', '.join(sorted(skipped))}" if skipped else ""))

        # --- Bank salary advice ---
        bank_rows = ["Employee,Employee Code,Account Number,IFSC/BIC,Net Pay"]
        skipped = []
        for slip in slips:
            lines = self._lines(slip)
            account = slip.employee_id.bank_account_id
            if not account:
                skipped.append(slip.employee_id.name)
                continue
            bank_rows.append(",".join(str(v) for v in [
                slip.employee_id.name,
                getattr(slip.employee_id, "employee_code", "") or "",
                account.acc_number,
                account.bank_id.bic or "",
                round(lines.get("NET", 0), 2),
            ]))
        self.bank_file = base64.b64encode("\n".join(bank_rows).encode("utf-8"))
        self.bank_filename = f"BankAdvice_{period_tag}.csv"
        notes.append(f"Bank advice: {len(bank_rows) - 1} transfer(s)."
                     + (f" Skipped (no bank account): {', '.join(skipped)}" if skipped else ""))

        self.summary = "\n".join(notes)
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
