from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class BproJoiningReport(models.Model):
    _name = "bpro.joining.report"
    _description = "Joining Report"
    _order = "sla_deadline"

    employee_id = fields.Many2one("hr.employee", required=True, ondelete="cascade")
    offer_id = fields.Many2one("bpro.job.offer", ondelete="set null")
    expected_joining_date = fields.Date(required=True)
    sla_deadline = fields.Date(
        compute="_compute_sla_deadline", store=True,
        help="expected_joining_date + the company's joining_report_sla "
        "policy, computed once at creation - not re-computed if the "
        "policy changes later, so existing joiners aren't retroactively "
        "made overdue by a policy tightening.",
    )
    state = fields.Selection(
        [("pending", "Pending"), ("submitted", "Submitted")],
        default="pending",
        required=True,
    )
    is_overdue = fields.Boolean(compute="_compute_is_overdue")
    actual_joining_date = fields.Date()
    submitted_date = fields.Datetime(readonly=True, copy=False)
    note = fields.Text()

    @api.depends("expected_joining_date")
    def _compute_sla_deadline(self):
        for rec in self:
            if not rec.expected_joining_date:
                rec.sla_deadline = False
                continue
            company = rec.employee_id.company_id or self.env.company
            days = int(company.joining_report_sla or "7")
            rec.sla_deadline = rec.expected_joining_date + timedelta(days=days)

    @api.depends("state", "sla_deadline")
    def _compute_is_overdue(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.is_overdue = bool(
                rec.state == "pending" and rec.sla_deadline and rec.sla_deadline < today
            )

    def action_submit(self):
        for rec in self:
            if rec.state == "submitted":
                raise UserError("This joining report was already submitted.")
            if not rec.actual_joining_date:
                raise UserError("Set the actual joining date before submitting.")
        self.write({
            "state": "submitted",
            "submitted_date": fields.Datetime.now(),
        })
