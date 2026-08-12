from odoo import fields, models
from odoo.exceptions import UserError


class BproEmployeeAsset(models.Model):
    _name = "bpro.employee.asset"
    _description = "Employee Asset (issue/return tracking)"
    _order = "issued_date desc"

    # Deliberately separate from bpro_plant's fixed-asset register -
    # that module tracks company plant/machinery for depreciation
    # accounting; this is simple issue/return tracking for IT equipment
    # handed to an individual employee, a different concern entirely.
    employee_id = fields.Many2one("hr.employee", required=True, ondelete="cascade")
    name = fields.Char(string="Asset", required=True, help="e.g. 'Dell Latitude 5420'")
    asset_type = fields.Selection(
        [
            ("laptop", "Laptop"),
            ("mobile", "Mobile Phone"),
            ("accessory", "Accessory"),
            ("other", "Other"),
        ],
        default="laptop",
        required=True,
    )
    serial_tag = fields.Char(string="Serial / Asset Tag")
    state = fields.Selection(
        [("issued", "Issued"), ("returned", "Returned")],
        default="issued",
        required=True,
    )
    issued_date = fields.Date(default=lambda self: fields.Date.context_today(self))
    returned_date = fields.Date()
    notes = fields.Text()

    def action_mark_returned(self):
        for rec in self:
            if rec.state == "returned":
                raise UserError(f"{rec.name} is already marked returned.")
        self.write({
            "state": "returned",
            "returned_date": fields.Date.context_today(self),
        })
