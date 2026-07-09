from odoo import api, fields, models


class BproQualityNonconformance(models.Model):
    _name = "bpro.quality.nonconformance"
    _description = "Quality Non-Conformance"
    _order = "id desc"

    name = fields.Char(required=True, copy=False, default="New")
    check_id = fields.Many2one("bpro.quality.check", required=True, ondelete="cascade")
    product_id = fields.Many2one(related="check_id.product_id", store=True)
    company_id = fields.Many2one(related="check_id.company_id", store=True)
    description = fields.Text()
    root_cause = fields.Text()
    corrective_action = fields.Text()
    responsible_user_id = fields.Many2one("res.users")
    state = fields.Selection(
        [("open", "Open"), ("investigating", "Investigating"), ("closed", "Closed")],
        default="open",
        required=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records.filtered(lambda r: r.name == "New"):
            record.name = f"NC/{record.id:05d}"
        return records
