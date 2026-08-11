from odoo import api, fields, models
from odoo.exceptions import UserError


class BproTdsDeclaration(models.Model):
    _name = "bpro.tds.declaration"
    _description = "TDS Investment Declaration"
    _order = "fy_start_year desc"

    contract_id = fields.Many2one("hr.contract", required=True, ondelete="cascade")
    employee_id = fields.Many2one(
        related="contract_id.employee_id", store=True, string="Employee"
    )
    fy_start_year = fields.Integer(
        required=True,
        default=lambda self: self._default_fy_start_year(),
        help="The calendar year the financial year STARTS in - "
        "FY2026-27 (1 Apr 2026 - 31 Mar 2027) is 2026.",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        default="draft",
        required=True,
    )
    declared_80c = fields.Float(
        string="Declared 80C Investments",
        help="PPF, ELSS, life insurance, home loan principal, tuition "
        "fees, 5-yr tax-saver FDs etc. combined. Capped at Rs.1,50,000 "
        "when applied to TDS - only relevant under the Old Regime.",
    )
    declared_80d = fields.Float(
        string="Declared 80D (Health Insurance Premium)",
        help="Capped at Rs.25,000 when applied to TDS - a simplification, "
        "since this build has no senior-citizen category yet (real 80D "
        "allows higher caps for senior citizens / senior-citizen "
        "parents). Only relevant under the Old Regime.",
    )
    monthly_rent = fields.Float(
        help="Used to compute HRA exemption under the Old Regime: "
        "min(actual HRA received, rent paid - 10% of basic, 40%/50% of "
        "basic). The 40%/50% split reuses the contract's own hra_percent "
        "as a metro/non-metro proxy (>=50 treated as metro) rather than "
        "a separate flag.",
    )
    note = fields.Text()
    approved_by = fields.Many2one("res.users", readonly=True, copy=False)
    approved_date = fields.Date(readonly=True, copy=False)

    _sql_constraints = [
        (
            "contract_fy_unique",
            "unique(contract_id, fy_start_year)",
            "Only one declaration per contract per financial year.",
        ),
    ]

    @api.model
    def _default_fy_start_year(self):
        today = fields.Date.context_today(self)
        return today.year if today.month >= 4 else today.year - 1

    def action_submit(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError("Only draft declarations can be submitted.")
        self.write({"state": "submitted"})

    def action_approve(self):
        for rec in self:
            if rec.state != "submitted":
                raise UserError("Only submitted declarations can be approved.")
        self.write({
            "state": "approved",
            "approved_by": self.env.user.id,
            "approved_date": fields.Date.context_today(self),
        })

    def action_reject(self):
        for rec in self:
            if rec.state not in ("submitted", "approved"):
                raise UserError("Only submitted or approved declarations can be rejected.")
        self.write({"state": "rejected", "approved_by": False, "approved_date": False})

    def action_reset_draft(self):
        self.write({"state": "draft", "approved_by": False, "approved_date": False})
