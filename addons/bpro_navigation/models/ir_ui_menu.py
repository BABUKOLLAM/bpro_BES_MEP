from odoo import fields, models


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    bpro_group_id = fields.Many2one(
        "bpro.menu.group",
        string="bpro App Group",
        help="Which section this app appears under in the bpro grouped "
        "apps menu (the grid icon, top-left). Only meaningful on an app's "
        "root menu (the one with no parent) - the apps menu only ever "
        "lists root menus, so grouping a submenu has no visible effect. "
        "Left blank, the app falls back to whichever bpro.menu.group has "
        "is_fallback set.",
    )
