from odoo import api, fields, models


class MaintenanceRequest(models.Model):
    _inherit = "maintenance.request"

    bpro_downtime_hours = fields.Float(
        compute="_compute_bpro_downtime_hours",
        store=True,
        help="Hours between request and close date, for closed corrective "
        "requests only - request_date/close_date are date-only fields, so "
        "this is a whole-day approximation, not to-the-minute.",
    )

    @api.depends("maintenance_type", "done", "request_date", "close_date")
    def _compute_bpro_downtime_hours(self):
        for request in self:
            if (
                request.maintenance_type == "corrective"
                and request.done
                and request.request_date
                and request.close_date
            ):
                request.bpro_downtime_hours = (
                    request.close_date - request.request_date
                ).days * 24.0
            else:
                request.bpro_downtime_hours = 0.0
