from odoo import fields, models


class BproReportColumn(models.Model):
    _name = "bpro.report.column"
    _description = "Selectable column for a bpro report's Excel export"
    _order = "report_model, sequence"

    name = fields.Char(required=True)
    technical_name = fields.Char(
        required=True, help="Field name on the report's line_ids model"
    )
    report_model = fields.Char(
        required=True, index=True, help="_name of the wizard this column belongs to"
    )
    sequence = fields.Integer(default=10)
