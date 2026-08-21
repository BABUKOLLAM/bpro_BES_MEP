{
    "name": "bpro Data Tools — Import/Export for Everyone",
    "summary": "Grants list-view Export to all internal users; pairs with the hosted import template pack",
    "description": """
Odoo gates the list-view Export action behind base.group_allow_export.
For ME Polymers every internal user is expected to move data in and out
of the system (bulk upload via gear > Import records, bulk download via
select > Export), so this module implies the export group on Internal
User. What each user can actually import/export is still bounded by
their role's read/create rights per model - this only reveals the
buttons, it grants no data access.

The matching per-module import templates (auto-mapping column headers +
directions) are served statically at /downloads/templates/.
""",
    "version": "18.0.1.0.0",
    "category": "Hidden",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": ["base"],
    "data": ["security/export_groups.xml"],
    "installable": True,
    "auto_install": False,
}
