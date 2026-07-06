from odoo import fields, models


class PmsGoalTraining(models.Model):
    """Link performance goals to eLearning courses: a goal can require
    completing one or more bpro LMS courses."""

    _inherit = "bpro.pms.goal"

    course_ids = fields.Many2many(
        "slide.channel",
        string="Required Courses",
        help="eLearning courses the employee should complete for this goal.",
    )
