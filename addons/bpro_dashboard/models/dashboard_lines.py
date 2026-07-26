from odoo import fields, models


class BproDashboardItemProductionLine(models.TransientModel):
    _name = "bpro.dashboard.item.production.line"
    _description = "Executive Dashboard - Item-wise Production (MTD)"

    dashboard_id = fields.Many2one("bpro.executive.dashboard", ondelete="cascade")
    product_id = fields.Many2one("product.product")
    achieved = fields.Float()
    target = fields.Float()
    balance = fields.Float()
    achievement_pct = fields.Float(string="Achievement %")


class BproDashboardItemSalesLine(models.TransientModel):
    _name = "bpro.dashboard.item.sales.line"
    _description = "Executive Dashboard - Item-wise Sales (Weekly)"

    dashboard_id = fields.Many2one("bpro.executive.dashboard", ondelete="cascade")
    product_id = fields.Many2one("product.product")
    actual = fields.Float()
    target = fields.Float()
    diff = fields.Float()
    achievement_pct = fields.Float(string="Achievement %")


class BproDashboardAreaSalesLine(models.TransientModel):
    _name = "bpro.dashboard.area.sales.line"
    _description = "Executive Dashboard - Area-wise Sales (Weekly)"

    dashboard_id = fields.Many2one("bpro.executive.dashboard", ondelete="cascade")
    sales_area_id = fields.Many2one("bpro.sales.area", string="Area")
    order_count = fields.Integer(string="Orders")
