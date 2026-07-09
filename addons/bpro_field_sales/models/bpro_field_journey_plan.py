from odoo import fields, models


class BproFieldJourneyPlan(models.Model):
    _name = "bpro.field.journey.plan"
    _description = "Field Sales Journey Plan"
    _order = "visit_date desc, id desc"

    employee_id = fields.Many2one("hr.employee", required=True, string="Salesperson")
    partner_id = fields.Many2one("res.partner", required=True, string="Dealer/Distributor")
    visit_date = fields.Date(required=True, default=fields.Date.context_today)
    purpose = fields.Char()
    state = fields.Selection(
        [("planned", "Planned"), ("visited", "Visited"), ("missed", "Missed")],
        default="planned",
        required=True,
    )
    visit_notes = fields.Text()
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )

    def action_mark_visited(self):
        self.write({"state": "visited"})

    def action_mark_missed(self):
        self.write({"state": "missed"})
