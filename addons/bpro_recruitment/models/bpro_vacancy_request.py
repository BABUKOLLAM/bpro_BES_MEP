from odoo import api, fields, models
from odoo.exceptions import UserError


class BproVacancyRequest(models.Model):
    _name = "bpro.vacancy.request"
    _description = "Vacancy Request"
    _order = "create_date desc"
    _rec_name = "job_title"

    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    department_id = fields.Many2one(
        "hr.department",
        required=True,
        default=lambda self: self._default_department_id(),
        help="Defaults to the requesting HOD's own department. Only "
        "group_client_hr can pick a different one.",
    )
    requested_by = fields.Many2one(
        "res.users", default=lambda self: self.env.user, readonly=True
    )
    job_title = fields.Char(required=True)
    positions_count = fields.Integer(default=1, required=True)
    employment_type = fields.Selection(
        [
            ("full_time", "Full-time"),
            ("part_time", "Part-time"),
            ("contract", "Contract"),
        ],
        default="full_time",
        required=True,
    )
    justification = fields.Text(required=True)
    target_joining_date = fields.Date()
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
    job_id = fields.Many2one(
        "hr.job",
        readonly=True,
        copy=False,
        help="Auto-created on approval - ready to publish via the "
        "public application page (website_hr_recruitment).",
    )
    rejection_reason = fields.Text()
    approved_by = fields.Many2one("res.users", readonly=True, copy=False)
    approved_date = fields.Date(readonly=True, copy=False)

    @api.model
    def _default_department_id(self):
        employee = self.env.user.employee_id
        return employee.department_id.id if employee else False

    def action_submit(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError("Only draft requests can be submitted.")
            if rec.positions_count < 1:
                raise UserError("Positions requested must be at least 1.")
        self.write({"state": "submitted"})

    def action_approve(self):
        for rec in self:
            if rec.state != "submitted":
                raise UserError("Only submitted requests can be approved.")
            # sudo(): approving a vacancy request is already gated to
            # group_client_hr (model access + the button's groups=) - that
            # is the real permission boundary here. Requiring the approver
            # to ALSO separately hold native hr_recruitment's own
            # "Officer" group just to create the resulting hr.job would be
            # a confusing second, unrelated gate on an action they're
            # already authorized to take.
            job = self.env["hr.job"].sudo().create({
                "name": rec.job_title,
                "company_id": rec.company_id.id,
                "department_id": rec.department_id.id,
                "no_of_recruitment": rec.positions_count,
            })
            rec.write({
                "state": "approved",
                "job_id": job.id,
                "approved_by": self.env.user.id,
                "approved_date": fields.Date.context_today(rec),
            })

    def action_reject(self):
        for rec in self:
            if rec.state != "submitted":
                raise UserError("Only submitted requests can be rejected.")
        self.write({"state": "rejected"})

    def action_reset_draft(self):
        for rec in self:
            if rec.state != "rejected":
                raise UserError("Only rejected requests can be reset to draft.")
        self.write({"state": "draft", "rejection_reason": False})
