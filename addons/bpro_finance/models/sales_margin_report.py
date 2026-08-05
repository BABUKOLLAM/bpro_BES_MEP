from collections import defaultdict

from odoo import api, fields, models


class BproSalesMarginWizard(models.TransientModel):
    _name = "bpro.sales.margin.wizard"
    _inherit = ["bpro.xlsx.export.mixin"]
    _description = "Sales Margin / Profitability Report"

    _xlsx_line_model = "bpro.sales.margin.line"
    _xlsx_export_fields = ["product_id", "qty_sold", "revenue", "cost", "margin", "margin_pct"]

    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True, default=fields.Date.context_today)
    line_ids = fields.One2many("bpro.sales.margin.line", "wizard_id", readonly=True)
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id
    )
    total_revenue = fields.Monetary(readonly=True)
    total_cost = fields.Monetary(readonly=True)
    total_margin = fields.Monetary(readonly=True)

    def action_generate(self):
        self.ensure_one()
        self.line_ids.unlink()
        data = self._get_sales_margin_data(self.env.company, self.date_from, self.date_to)
        self.line_ids = [(0, 0, vals) for vals in data["lines"]]
        self.total_revenue = data["total_revenue"]
        self.total_cost = data["total_cost"]
        self.total_margin = data["total_margin"]
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.model
    def _get_sales_margin_data(self, company, date_from, date_to):
        """Revenue and margin per product, from confirmed sale order lines
        whose order date falls in the period. Cost is quantity sold x the
        product's CURRENT standard_price - since this is standard costing
        (not FIFO/lot costing), a cost change after the sale is not
        reflected retroactively; this is a known, deliberate limitation of
        standard costing, not a bug."""
        order_lines = self.env["sale.order.line"].search(
            [
                ("order_id.company_id", "=", company.id),
                ("order_id.state", "=", "sale"),
                ("order_id.date_order", ">=", date_from),
                ("order_id.date_order", "<=", date_to),
                ("display_type", "=", False),
            ]
        )
        by_product = defaultdict(lambda: {"qty": 0.0, "revenue": 0.0})
        for line in order_lines:
            product = line.product_id
            if not product:
                continue
            bucket = by_product[product]
            bucket["qty"] += line.product_uom_qty
            bucket["revenue"] += line.price_subtotal

        lines = []
        total_revenue = 0.0
        total_cost = 0.0
        for product, bucket in by_product.items():
            cost = bucket["qty"] * (product.standard_price or 0.0)
            revenue = bucket["revenue"]
            margin = revenue - cost
            margin_pct = (margin / revenue) if revenue else 0.0
            total_revenue += revenue
            total_cost += cost
            lines.append(
                {
                    "product_id": product.id,
                    "qty_sold": bucket["qty"],
                    "revenue": revenue,
                    "cost": cost,
                    "margin": margin,
                    "margin_pct": margin_pct,
                }
            )
        lines.sort(key=lambda l: l["margin"], reverse=True)
        return {
            "lines": lines,
            "total_revenue": total_revenue,
            "total_cost": total_cost,
            "total_margin": total_revenue - total_cost,
        }


class BproSalesMarginLine(models.TransientModel):
    _name = "bpro.sales.margin.line"
    _description = "Sales Margin Report Line"
    _order = "id"

    wizard_id = fields.Many2one("bpro.sales.margin.wizard", required=True, ondelete="cascade")
    currency_id = fields.Many2one(related="wizard_id.currency_id")
    product_id = fields.Many2one("product.product", required=True)
    qty_sold = fields.Float()
    revenue = fields.Monetary()
    cost = fields.Monetary()
    margin = fields.Monetary()
    margin_pct = fields.Float(string="Margin %")
