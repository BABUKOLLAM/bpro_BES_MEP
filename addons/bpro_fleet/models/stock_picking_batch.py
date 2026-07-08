from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockPickingBatch(models.Model):
    _inherit = "stock.picking.batch"

    currency_id = fields.Many2one(related="company_id.currency_id")
    bpro_trip_cost = fields.Monetary(
        compute="_compute_bpro_trip_cost", store=True, readonly=False
    )
    bpro_transporter_bill_id = fields.Many2one(
        "account.move", string="Transporter Bill", readonly=True, copy=False
    )

    @api.depends("vehicle_id")
    def _compute_bpro_trip_cost(self):
        for batch in self:
            if batch.vehicle_id.bpro_ownership_type == "hired":
                batch.bpro_trip_cost = batch.vehicle_id.bpro_trip_rate
            else:
                batch.bpro_trip_cost = 0.0

    def action_bpro_create_transporter_bill(self):
        for batch in self:
            vehicle = batch.vehicle_id
            if vehicle.bpro_ownership_type != "hired":
                raise UserError(
                    _("%s is not assigned a hired/external vehicle.") % batch.name
                )
            if batch.state != "done":
                raise UserError(
                    _("%s must be done before billing the transporter.") % batch.name
                )
            if batch.bpro_transporter_bill_id:
                raise UserError(
                    _("%s already has a transporter bill.") % batch.name
                )
            move = self.env["account.move"].create(
                {
                    "move_type": "in_invoice",
                    "partner_id": vehicle.bpro_transporter_id.id,
                    "company_id": batch.company_id.id,
                    "invoice_origin": batch.name,
                    "invoice_line_ids": [
                        (
                            0,
                            0,
                            {
                                "name": _("Trip cost - %s (%s)")
                                % (batch.name, vehicle.display_name),
                                "quantity": 1,
                                "price_unit": batch.bpro_trip_cost,
                                "account_id": vehicle.bpro_trip_expense_account_id.id,
                            },
                        )
                    ],
                }
            )
            batch.bpro_transporter_bill_id = move.id
