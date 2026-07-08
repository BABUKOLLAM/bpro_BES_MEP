from odoo import fields, models


class MaintenanceEquipment(models.Model):
    _inherit = "maintenance.equipment"

    # Odoo's Enterprise edition bridges maintenance.equipment to
    # mrp.workcenter natively; that bridge module doesn't exist in this
    # Community image, so machinery and the work centers they run on are
    # otherwise two disconnected models.
    workcenter_id = fields.Many2one("mrp.workcenter", string="Work Center")
