import base64
import io

import xlsxwriter

from odoo import _, fields, models
from odoo.exceptions import UserError


class BproXlsxExportMixin(models.AbstractModel):
    """Generic 'export this wizard's line_ids to Excel, with a column
    picker' action. Concrete wizards inherit this and set two class
    attributes - _xlsx_line_model and _xlsx_export_fields - describing
    which fields on their line_ids model are offered as columns; the
    actual bpro.report.column rows are seeded via each addon's own data
    file (keyed by report_model = the wizard's _name)."""

    _name = "bpro.xlsx.export.mixin"
    _description = "Excel export with selectable columns, for bpro report wizards"

    _xlsx_line_model = None
    _xlsx_export_fields = []

    xlsx_column_ids = fields.Many2many(
        "bpro.report.column",
        string="Columns to Export",
        default=lambda self: self._default_xlsx_column_ids(),
    )
    xlsx_file = fields.Binary(readonly=True, attachment=False)
    xlsx_filename = fields.Char(readonly=True)

    def _default_xlsx_column_ids(self):
        return self.env["bpro.report.column"].search([("report_model", "=", self._name)])

    def action_export_xlsx(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("Generate the report before exporting to Excel."))
        columns = self.xlsx_column_ids or self._default_xlsx_column_ids()
        if not columns:
            raise UserError(_("No columns available to export."))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet_name = (self._description or self._name)[:31]
        for ch in ":\\/?*[]":
            sheet_name = sheet_name.replace(ch, " ")
        sheet = workbook.add_worksheet(sheet_name)

        header_fmt = workbook.add_format(
            {"bold": True, "bg_color": "#D9E1F2", "border": 1}
        )
        num_fmt = workbook.add_format({"num_format": "#,##0.00", "border": 1})
        text_fmt = workbook.add_format({"border": 1})

        for col_idx, column in enumerate(columns):
            sheet.write(0, col_idx, column.name, header_fmt)
            sheet.set_column(col_idx, col_idx, max(14, len(column.name) + 2))

        for row_idx, line in enumerate(self.line_ids, start=1):
            for col_idx, column in enumerate(columns):
                value = line[column.technical_name]
                if isinstance(value, models.BaseModel):
                    sheet.write(row_idx, col_idx, value.display_name if value else "", text_fmt)
                elif isinstance(value, bool):
                    sheet.write(row_idx, col_idx, "Yes" if value else "", text_fmt)
                elif isinstance(value, (int, float)):
                    sheet.write(row_idx, col_idx, value, num_fmt)
                else:
                    sheet.write(row_idx, col_idx, value or "", text_fmt)

        workbook.close()
        output.seek(0)
        self.xlsx_file = base64.b64encode(output.read())
        self.xlsx_filename = f"{sheet_name}.xlsx"

        return {
            "type": "ir.actions.act_url",
            "url": (
                f"/web/content?model={self._name}&id={self.id}&field=xlsx_file"
                f"&filename_field=xlsx_filename&download=true"
            ),
            "target": "self",
        }
