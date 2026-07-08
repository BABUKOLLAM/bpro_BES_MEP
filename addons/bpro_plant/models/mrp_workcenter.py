from odoo import fields, models


class MrpWorkcenter(models.Model):
    _inherit = "mrp.workcenter"

    bpro_equipment_ids = fields.One2many(
        "maintenance.equipment", "workcenter_id", string="Equipment"
    )
