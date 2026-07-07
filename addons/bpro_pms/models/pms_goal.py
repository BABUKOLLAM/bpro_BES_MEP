from odoo import api, fields, models


class PmsGoal(models.Model):
    _name = "bpro.pms.goal"
    _description = "Performance Goal"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "deadline asc, id desc"

    name = fields.Char(string="Goal", required=True, tracking=True)
    description = fields.Html(string="Description")
    employee_id = fields.Many2one(
        "hr.employee", string="Employee", required=True, tracking=True
    )
    manager_id = fields.Many2one(
        "hr.employee",
        string="Manager",
        related="employee_id.parent_id",
        store=True,
        readonly=True,
    )
    department_id = fields.Many2one(
        "hr.department",
        string="Department",
        related="employee_id.department_id",
        store=True,
        readonly=True,
    )
    cycle_id = fields.Many2one(
        "bpro.pms.cycle", string="Review Cycle", tracking=True
    )
    weight = fields.Integer(
        string="Weight (%)",
        default=25,
        help="Relative importance of this goal within the review cycle.",
    )
    target = fields.Char(string="Target / Success Criteria")
    progress = fields.Integer(string="Progress (%)", default=0, tracking=True)
    deadline = fields.Date(string="Deadline", tracking=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "In Progress"),
            ("done", "Achieved"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, required=True
    )

    _sql_constraints = [
        (
            "progress_range",
            "CHECK(progress >= 0 AND progress <= 100)",
            "Progress must be between 0 and 100.",
        ),
        (
            "weight_range",
            "CHECK(weight >= 0 AND weight <= 100)",
            "Weight must be between 0 and 100.",
        ),
    ]

    def action_activate(self):
        return self.write({"state": "active"})

    def action_done(self):
        return self.write({"state": "done", "progress": 100})

    def action_cancel(self):
        return self.write({"state": "cancelled"})

    def action_reset_draft(self):
        return self.write({"state": "draft"})
