from odoo import api, fields, models


class HrEmployee(models.Model):
    """Employee 360 (roadmap P6): performance history on the employee."""

    _inherit = "hr.employee"

    pms_goal_ids = fields.One2many("bpro.pms.goal", "employee_id", string="Goals")
    pms_appraisal_ids = fields.One2many(
        "bpro.pms.appraisal", "employee_id", string="Appraisals"
    )
    pms_training_need_ids = fields.One2many(
        "bpro.pms.training.need", "employee_id", string="Training Needs"
    )
    pms_goal_progress = fields.Integer(
        string="Avg Goal Progress (%)", compute="_compute_pms_360"
    )
    pms_last_rating = fields.Char(string="Last Rating", compute="_compute_pms_360")

    @api.depends("pms_goal_ids.progress", "pms_appraisal_ids.rating")
    def _compute_pms_360(self):
        rating_labels = dict(
            self.env["bpro.pms.appraisal"]._fields["rating"].selection
        )
        for emp in self:
            goals = emp.pms_goal_ids.filtered(lambda g: g.state in ("active", "done"))
            emp.pms_goal_progress = (
                int(sum(goals.mapped("progress")) / len(goals)) if goals else 0
            )
            done = emp.pms_appraisal_ids.filtered(
                lambda a: a.state == "done" and a.rating
            ).sorted("id")
            emp.pms_last_rating = rating_labels.get(done[-1].rating) if done else False
