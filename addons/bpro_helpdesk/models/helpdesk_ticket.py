from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class BproHelpdeskTicket(models.Model):
    _name = "bpro.helpdesk.ticket"
    _description = "Helpdesk Ticket"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(string="Subject", required=True, tracking=True)
    partner_id = fields.Many2one(
        "res.partner", string="Customer", required=True, tracking=True
    )
    description = fields.Text()
    priority = fields.Selection(
        [("0", "Low"), ("1", "Medium"), ("2", "High"), ("3", "Urgent")],
        default="1",
        tracking=True,
    )
    team_id = fields.Many2one("bpro.helpdesk.team", tracking=True)
    user_id = fields.Many2one("res.users", string="Assigned To", tracking=True)
    # Optional link back to the originating order - closes the loop with
    # Sales, so a customer's support history is visible from their record.
    sale_order_id = fields.Many2one("sale.order", string="Related Order")
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    stage_id = fields.Many2one(
        "bpro.helpdesk.stage",
        required=True,
        default=lambda self: self._default_stage(),
        group_expand="_read_group_stage_ids",
        tracking=True,
    )
    is_closed = fields.Boolean(related="stage_id.is_closed", store=True)
    sla_deadline = fields.Datetime(compute="_compute_sla_deadline", store=True)
    is_overdue = fields.Boolean(
        compute="_compute_is_overdue", search="_search_is_overdue"
    )
    close_date = fields.Datetime(readonly=True, copy=False)
    resolution_hours = fields.Float(
        compute="_compute_resolution_hours", store=True, digits=(16, 2)
    )

    @api.model
    def _default_stage(self):
        return self.env["bpro.helpdesk.stage"].search([], order="sequence", limit=1)

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        return stages.search([], order="sequence")

    @api.depends("create_date", "company_id")
    def _compute_sla_deadline(self):
        for ticket in self:
            if not ticket.create_date:
                ticket.sla_deadline = False
                continue
            hours = self.env["bpro.policy"].get_value(
                ticket.company_id or self.env.company,
                "helpdesk_sla_response_hours",
                default=24.0,
            )
            ticket.sla_deadline = ticket.create_date + relativedelta(hours=hours)

    @api.depends("sla_deadline", "is_closed")
    def _compute_is_overdue(self):
        now = fields.Datetime.now()
        for ticket in self:
            ticket.is_overdue = bool(
                ticket.sla_deadline and not ticket.is_closed and now > ticket.sla_deadline
            )

    @api.model
    def _search_is_overdue(self, operator, value):
        now = fields.Datetime.now()
        want_overdue = (operator == "=") == bool(value)
        if want_overdue:
            return [("sla_deadline", "<", now), ("is_closed", "=", False)]
        return ["|", ("sla_deadline", ">=", now), ("is_closed", "=", True)]

    @api.depends("close_date", "create_date")
    def _compute_resolution_hours(self):
        for ticket in self:
            if ticket.close_date and ticket.create_date:
                ticket.resolution_hours = (
                    ticket.close_date - ticket.create_date
                ).total_seconds() / 3600.0
            else:
                ticket.resolution_hours = 0.0

    def write(self, vals):
        res = super().write(vals)
        if "stage_id" in vals:
            for ticket in self:
                if ticket.stage_id.is_closed and not ticket.close_date:
                    ticket.close_date = fields.Datetime.now()
                elif not ticket.stage_id.is_closed and ticket.close_date:
                    ticket.close_date = False
        return res

    def action_bpro_close(self):
        closing_stage = self.env["bpro.helpdesk.stage"].search(
            [("is_closed", "=", True)], order="sequence", limit=1
        )
        for ticket in self:
            ticket.stage_id = closing_stage
