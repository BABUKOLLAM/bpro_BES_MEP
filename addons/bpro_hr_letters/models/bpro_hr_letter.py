from odoo import api, fields, models
from odoo.exceptions import UserError


class BproHrLetter(models.Model):
    _name = "bpro.hr.letter"
    _description = "HR Letter"
    _order = "create_date desc"
    _rec_name = "reference"

    reference = fields.Char(readonly=True, copy=False, default="New")
    employee_id = fields.Many2one("hr.employee", required=True, ondelete="restrict")
    company_id = fields.Many2one(related="employee_id.company_id", store=True)
    letter_type = fields.Selection(
        [
            ("salary_certificate", "Salary Certificate"),
            ("address_proof", "Address Proof"),
            ("experience", "Experience / Relieving Letter"),
            ("increment", "Increment Letter"),
        ],
        required=True,
        default="salary_certificate",
    )
    letter_date = fields.Date(
        default=lambda self: fields.Date.context_today(self), required=True
    )

    # Snapshot fields, filled at creation from the contract - a letter
    # is a statement about a point in time; it must not silently change
    # when the contract later does.
    designation = fields.Char()
    ctc_annual = fields.Float(string="Annual CTC")
    monthly_gross = fields.Float()
    service_from = fields.Date()
    service_to = fields.Date(help="Experience letters only - blank means still serving.")
    revised_ctc = fields.Float(
        string="Revised Annual CTC",
        help="Increment letters only - the new CTC being communicated. "
        "Updating the contract itself remains a separate HR action.",
    )
    note = fields.Text(help="Optional extra paragraph printed on the letter.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("reference", "New") == "New":
                vals["reference"] = self.env["ir.sequence"].next_by_code(
                    "bpro.hr.letter"
                ) or "New"
        letters = super().create(vals_list)
        for letter in letters:
            if not letter.designation or not letter.ctc_annual:
                letter._snapshot_from_contract()
        return letters

    def _snapshot_from_contract(self):
        self.ensure_one()
        contract = self.env["hr.contract"].sudo().search(
            [("employee_id", "=", self.employee_id.id), ("state", "=", "open")],
            order="date_start desc", limit=1,
        )
        vals = {}
        if not self.designation:
            vals["designation"] = self.employee_id.job_id.name or (
                contract.job_id.name if contract else ""
            )
        if contract:
            monthly_basic = contract.ctc_annual / 12.0 * (contract.basic_percent / 100.0)
            vals.setdefault("ctc_annual", contract.ctc_annual)
            vals["monthly_gross"] = monthly_basic * (1 + contract.hra_percent / 100.0)
            vals["service_from"] = contract.date_start
            first = self.env["hr.contract"].sudo().search(
                [("employee_id", "=", self.employee_id.id)],
                order="date_start asc", limit=1,
            )
            if first:
                vals["service_from"] = first.date_start
        self.write(vals)

    def action_print(self):
        self.ensure_one()
        if self.letter_type == "increment" and not self.revised_ctc:
            raise UserError("Set the revised CTC before printing an increment letter.")
        return self.env.ref("bpro_hr_letters.action_report_hr_letter").report_action(self)
