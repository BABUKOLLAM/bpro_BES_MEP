from odoo import api, fields, models


class PmsGoalTraining(models.Model):
    """Link performance goals to eLearning courses: a goal can require
    completing one or more bpro LMS courses."""

    _inherit = "bpro.pms.goal"

    course_ids = fields.Many2many(
        "slide.channel",
        string="Required Courses",
        help="eLearning courses the employee should complete for this goal.",
    )
    training_progress = fields.Integer(
        string="Training Progress (%)",
        compute="_compute_training_progress",
        help="Average completion of the required courses for this employee. "
        "Courses not yet started count as 0%.",
    )

    @api.depends("course_ids", "employee_id")
    def _compute_training_progress(self):
        Membership = self.env["slide.channel.partner"].sudo()
        for goal in self:
            partner = goal.employee_id._lms_partner() if goal.employee_id else None
            if not goal.course_ids or not partner:
                goal.training_progress = 0
                continue
            memberships = Membership.search(
                [
                    ("channel_id", "in", goal.course_ids.ids),
                    ("partner_id", "=", partner.id),
                ]
            )
            by_channel = {m.channel_id.id: m.completion for m in memberships}
            total = sum(by_channel.get(c, 0) for c in goal.course_ids.ids)
            goal.training_progress = int(total / len(goal.course_ids))
