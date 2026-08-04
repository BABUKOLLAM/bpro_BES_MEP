from odoo import api, fields, models


class BproStockSummaryWizard(models.TransientModel):
    _name = "bpro.stock.summary.wizard"
    _description = "Stock Summary"

    as_of_date = fields.Date(required=True, default=fields.Date.context_today)
    line_ids = fields.One2many("bpro.stock.summary.line", "wizard_id", readonly=True)
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id
    )
    total_value = fields.Monetary(readonly=True)

    def action_generate(self):
        self.ensure_one()
        self.line_ids.unlink()
        data = self._get_stock_summary_data(self.env.company)
        self.line_ids = [(0, 0, vals) for vals in data["lines"]]
        self.total_value = data["total_value"]
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.model
    def _get_stock_summary_data(self, company):
        quants = self.env["stock.quant"].search(
            [
                ("company_id", "=", company.id),
                ("location_id.usage", "=", "internal"),
                ("quantity", "!=", 0),
            ]
        )
        lines = []
        total_value = 0.0
        for quant in quants.sorted(
            key=lambda q: (q.product_id.display_name, q.location_id.complete_name)
        ):
            cost = quant.product_id.standard_price or 0.0
            value = quant.quantity * cost
            total_value += value
            lines.append(
                {
                    "product_id": quant.product_id.id,
                    "location_id": quant.location_id.id,
                    "quantity": quant.quantity,
                    "uom_id": quant.product_uom_id.id,
                    "unit_cost": cost,
                    "value": value,
                }
            )
        return {"lines": lines, "total_value": total_value}


class BproStockSummaryLine(models.TransientModel):
    _name = "bpro.stock.summary.line"
    _description = "Stock Summary Line"
    _order = "id"

    wizard_id = fields.Many2one("bpro.stock.summary.wizard", required=True, ondelete="cascade")
    currency_id = fields.Many2one(related="wizard_id.currency_id")
    product_id = fields.Many2one("product.product", required=True)
    location_id = fields.Many2one("stock.location", required=True)
    quantity = fields.Float()
    uom_id = fields.Many2one("uom.uom")
    unit_cost = fields.Monetary()
    value = fields.Monetary()
