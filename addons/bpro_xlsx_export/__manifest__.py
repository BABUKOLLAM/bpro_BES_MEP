{
    "name": "bpro Excel Export",
    "summary": "Generic 'export report lines to Excel, with a selectable-column picker' building block",
    "description": """
Small foundational addon providing one reusable mixin
(bpro.xlsx.export.mixin) that any bpro report wizard can inherit to get
an "Export to Excel" action. Each report registers its own selectable
columns as bpro.report.column records; the user picks a subset (or
leaves all selected) before exporting, and the wizard's already-generated
line_ids are written out as an .xlsx download.

Kept separate from bpro_finance/bpro_inventory since both need it and
neither should depend on the other.
""",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
    ],
    "installable": True,
    "application": False,
}
