from datetime import date as date_type

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class BproShiftAssignment(models.Model):
    _name = "bpro.shift.assignment"
    _description = "Shift Assignment"
    _order = "date_from desc"

    employee_id = fields.Many2one("hr.employee", required=True, ondelete="cascade")
    calendar_id = fields.Many2one(
        "resource.calendar", required=True, string="Shift",
        help="A shift IS a working calendar - Shift A/B seeds included, "
        "add more for the plant's real roster.",
    )
    date_from = fields.Date(required=True, default=lambda self: fields.Date.context_today(self))
    date_to = fields.Date(help="Blank = open-ended (until superseded).")
    note = fields.Char()

    @api.constrains("employee_id", "date_from", "date_to")
    def _check_overlap(self):
        for rec in self:
            domain = [
                ("employee_id", "=", rec.employee_id.id),
                ("id", "!=", rec.id),
                ("date_from", "<=", rec.date_to or date_type.max),
            ]
            others = self.search(domain)
            overlapping = others.filtered(
                lambda o: (o.date_to or date_type.max) >= rec.date_from
            )
            if overlapping:
                raise ValidationError(
                    f"{rec.employee_id.name} already has a shift assignment "
                    "overlapping this period - end it first, two calendars "
                    "can't both apply on the same day."
                )

    @api.model_create_multi
    def create(self, vals_list):
        assignments = super().create(vals_list)
        # An assignment already in force applies immediately - the cron
        # only handles future-dated rotations taking effect later.
        assignments._apply_current()
        return assignments

    def write(self, vals):
        res = super().write(vals)
        self._apply_current()
        return res

    def _apply_current(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.date_from <= today and (not rec.date_to or rec.date_to >= today):
                rec.employee_id.resource_calendar_id = rec.calendar_id

    @api.model
    def _cron_apply_todays_shifts(self):
        """Daily: point every employee with an assignment covering today
        at that assignment's calendar - so rotations entered in advance
        flip on the right morning. Employees with no assignment at all
        are left alone (they keep whatever calendar HR set directly)."""
        today = fields.Date.context_today(self)
        current = self.search([
            ("date_from", "<=", today),
            "|", ("date_to", "=", False), ("date_to", ">=", today),
        ])
        for rec in current:
            if rec.employee_id.resource_calendar_id != rec.calendar_id:
                rec.employee_id.resource_calendar_id = rec.calendar_id
        return True
