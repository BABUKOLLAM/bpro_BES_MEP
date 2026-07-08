from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    bpro_ownership_type = fields.Selection(
        [("owned", "Owned"), ("hired", "Hired / External")],
        default="owned",
        required=True,
    )
    bpro_transporter_id = fields.Many2one(
        "res.partner",
        string="Transporter",
        help="The external vendor providing this vehicle - required for hired vehicles.",
    )
    bpro_trip_rate = fields.Monetary(
        string="Default Trip Rate",
        help="Default cost per delivery trip for this hired vehicle, used to "
        "prefill a batch's trip cost.",
    )
    bpro_trip_expense_account_id = fields.Many2one(
        "account.account",
        string="Trip Expense Account",
        help="Account used on the transporter bill line for this vehicle's trips.",
    )

    @api.constrains("bpro_ownership_type", "bpro_transporter_id", "bpro_trip_expense_account_id")
    def _check_bpro_hired_requires_transporter(self):
        for vehicle in self:
            if vehicle.bpro_ownership_type == "hired" and not (
                vehicle.bpro_transporter_id and vehicle.bpro_trip_expense_account_id
            ):
                raise ValidationError(
                    _(
                        "%s is marked Hired / External - a transporter and a "
                        "trip expense account must both be set."
                    )
                    % vehicle.display_name
                )
