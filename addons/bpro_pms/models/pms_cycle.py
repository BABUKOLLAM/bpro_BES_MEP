from odoo import api, fields, models


class PmsCycle(models.Model):
    _name = "bpro.pms.cycle"
    _description = "Performance Review Cycle"
    _order = "date_start desc"

    name = fields.Char(string="Cycle", required=True)
    date_start = fields.Date(string="Start Date", required=True)
    date_end = fields.Date(string="End Date", required=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("open", "Open"),
            ("closed", "Closed"),
        ],
        default="draft",
    )
    goal_ids = fields.One2many("bpro.pms.goal", "cycle_id", string="Goals")
    appraisal_ids = fields.One2many(
        "bpro.pms.appraisal", "cycle_id", string="Appraisals"
    )
    goal_count = fields.Integer(compute="_compute_counts")
    appraisal_count = fields.Integer(compute="_compute_counts")
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, required=True
    )

    _sql_constraints = [
        (
            "dates_order",
            "CHECK(date_end >= date_start)",
            "The cycle end date must be after the start date.",
        ),
    ]

    @api.depends("goal_ids", "appraisal_ids")
    def _compute_counts(self):
        for cycle in self:
            cycle.goal_count = len(cycle.goal_ids)
            cycle.appraisal_count = len(cycle.appraisal_ids)

    def action_open(self):
        return self.write({"state": "open"})

    def action_close(self):
        return self.write({"state": "closed"})
