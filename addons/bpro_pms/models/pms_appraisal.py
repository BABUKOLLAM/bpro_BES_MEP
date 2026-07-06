from odoo import api, fields, models


class PmsAppraisal(models.Model):
    _name = "bpro.pms.appraisal"
    _description = "Performance Appraisal"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(compute="_compute_name", store=True)
    employee_id = fields.Many2one(
        "hr.employee", string="Employee", required=True, tracking=True
    )
    reviewer_id = fields.Many2one(
        "hr.employee", string="Reviewer", required=True, tracking=True
    )
    cycle_id = fields.Many2one(
        "bpro.pms.cycle", string="Review Cycle", required=True
    )
    goal_ids = fields.One2many(
        "bpro.pms.goal",
        compute="_compute_goal_ids",
        string="Goals in Cycle",
    )
    self_assessment = fields.Html(string="Self Assessment")
    manager_feedback = fields.Html(string="Manager Feedback")
    rating = fields.Selection(
        [
            ("1", "Needs Improvement"),
            ("2", "Below Expectations"),
            ("3", "Meets Expectations"),
            ("4", "Exceeds Expectations"),
            ("5", "Outstanding"),
        ],
        string="Overall Rating",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("self", "Self Assessment"),
            ("review", "Manager Review"),
            ("done", "Completed"),
        ],
        default="draft",
        tracking=True,
    )
    training_need_ids = fields.One2many(
        "bpro.pms.training.need", "appraisal_id", string="Training Needs"
    )
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, required=True
    )

    @api.depends("employee_id", "cycle_id")
    def _compute_name(self):
        for rec in self:
            rec.name = (
                f"{rec.employee_id.name or ''} — {rec.cycle_id.name or ''}".strip(" —")
                or "New Appraisal"
            )

    @api.depends("employee_id", "cycle_id")
    def _compute_goal_ids(self):
        for rec in self:
            rec.goal_ids = self.env["bpro.pms.goal"].search(
                [
                    ("employee_id", "=", rec.employee_id.id),
                    ("cycle_id", "=", rec.cycle_id.id),
                ]
            )

    def action_start_self(self):
        return self.write({"state": "self"})

    def action_submit_review(self):
        return self.write({"state": "review"})

    def action_done(self):
        res = self.write({"state": "done"})
        self.training_need_ids._auto_enroll()
        return res
