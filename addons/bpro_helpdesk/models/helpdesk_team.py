from odoo import fields, models


class BproHelpdeskTeam(models.Model):
    _name = "bpro.helpdesk.team"
    _description = "Helpdesk Team"

    name = fields.Char(required=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    member_ids = fields.Many2many("res.users", string="Members")
    ticket_ids = fields.One2many("bpro.helpdesk.ticket", "team_id", string="Tickets")
    ticket_count = fields.Integer(compute="_compute_ticket_count")

    def _compute_ticket_count(self):
        for team in self:
            team.ticket_count = len(team.ticket_ids)
