{
    "name": "bpro Navigation — Grouped Apps Menu",
    "summary": "Replaces the flat apps-switcher dropdown with a grouped menu "
    "(Sales / Production / Accounts / HR / General, admin-configurable)",
    "description": """
Odoo's own apps switcher (the grid icon, top-left) is a flat, unordered
list - every installed app in one column, no way to tell "what kind of
app is this" at a glance. Once a deployment has 20+ apps installed, that
becomes a real everyday friction point, not a cosmetic one.

This module doesn't reorder that flat list (see bpro_base's menu sequence
script for that) - it replaces the list's structure entirely, grouping
apps under named section headers.

* New model bpro.menu.group: a handful of named, ordered buckets (seeded
  here as Sales / Production / Accounts / HR / General, but this is plain
  data - rename, reorder, or add buckets via Settings > Technical > bpro
  App Groups, no code change needed).
* ir.ui.menu gets one new field, bpro_group_id, editable on the existing
  native Menu Items form (Settings > Technical > User Interface > Menu
  Items) - assign any app's root menu to a group the same way.
* A post_init_hook seeds a best-effort default mapping for every app this
  client currently has installed. It resolves each app's root menu by
  external ID with raise_if_not_found=False - deliberately no hard
  manifest dependency on any of the apps being grouped (CRM, Sales, MRP,
  Purchase, Fleet, Maintenance, Payroll, ...), so this module installs
  cleanly regardless of which of those a given client has. An app not in
  the seed table (including anything installed later) falls back to
  whichever group has is_fallback = True (General, by default) - handled
  client-side, not by more seed data.
* The apps-menu dropdown itself is patched in place (QWeb t-inherit
  extension on web.NavBar.AppsMenu, plus a small NavBar JS patch) - one
  ORM call on nav-bar mount fetches the grouping, then the same
  DropdownItem markup Odoo already uses is rendered under a small
  uppercase section header per group instead of one flat column.
""",
    "version": "18.0.1.0.0",
    "category": "Technical",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": ["base", "web"],
    "data": [
        "security/ir.model.access.csv",
        "data/bpro_menu_group_data.xml",
        "views/bpro_menu_group_views.xml",
        "views/ir_ui_menu_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "bpro_navigation/static/src/webclient/navbar/navbar_patch.js",
            "bpro_navigation/static/src/webclient/navbar/navbar_patch.xml",
            "bpro_navigation/static/src/webclient/navbar/navbar_patch.scss",
        ],
    },
    "post_init_hook": "assign_default_menu_groups",
    "installable": True,
    "application": False,
}
