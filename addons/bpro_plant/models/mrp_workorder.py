from odoo import _, api, fields, models


class MrpWorkorder(models.Model):
    _inherit = "mrp.workorder"

    bpro_plant_maintenance_warning = fields.Char(
        compute="_compute_bpro_plant_maintenance_warning"
    )

    @api.depends(
        "workcenter_id.bpro_equipment_ids.maintenance_ids.done",
        "workcenter_id.bpro_equipment_ids.maintenance_ids.maintenance_type",
    )
    def _compute_bpro_plant_maintenance_warning(self):
        for workorder in self:
            open_requests = (
                workorder.workcenter_id.bpro_equipment_ids.maintenance_ids.filtered(
                    lambda r: r.maintenance_type == "corrective" and not r.done
                )
            )
            if open_requests:
                workorder.bpro_plant_maintenance_warning = _(
                    "%s on this work center has an open corrective maintenance "
                    "request - output here may be unreliable until it's resolved."
                ) % ", ".join(open_requests.equipment_id.mapped("name"))
            else:
                workorder.bpro_plant_maintenance_warning = False
