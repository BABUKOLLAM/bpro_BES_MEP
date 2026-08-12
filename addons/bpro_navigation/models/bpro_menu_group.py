from odoo import fields, models


class BproMenuGroup(models.Model):
    _name = "bpro.menu.group"
    _description = "Named section of the bpro grouped apps menu"
    _order = "sequence, id"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    is_fallback = fields.Boolean(
        string="Fallback Group",
        help="Apps with no group assigned (including newly installed apps "
        "nobody has sorted yet) land here. Exactly one group should have "
        "this set - if more than one does, the apps menu just uses "
        "whichever one it finds first.",
    )
    menu_ids = fields.One2many(
        "ir.ui.menu", "bpro_group_id", string="Apps in this Group"
    )
