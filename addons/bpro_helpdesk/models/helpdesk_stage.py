from odoo import fields, models


class BproHelpdeskStage(models.Model):
    _name = "bpro.helpdesk.stage"
    _description = "Helpdesk Ticket Stage"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    is_closed = fields.Boolean(
        string="Closing Stage",
        help="Tickets reaching a closing stage stop counting toward SLA "
        "overdue and get their resolution time recorded.",
    )
    fold = fields.Boolean(string="Folded in Kanban")
