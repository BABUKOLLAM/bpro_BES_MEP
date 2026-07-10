{
    "name": "bpro Executive Dashboard",
    "summary": "One-glance cross-module KPI dashboard tying together all 10 BES modules",
    "description": """
A capstone reporting layer, not a new operational module - pulls one
primary KPI from each of the 10 BES modules already built into a single
screen, reusing each module's own existing computation rather than
duplicating logic (the Finance section calls straight into
bpro.finance.dashboard's own _get_kpi_data).

Blends two kinds of signal deliberately:
* "Flow" metrics scoped to month-to-date, for modules with a clean
  business date (Sales revenue, Manufacturing output variance,
  Logistics on-time delivery %).
* "Stock" metrics read as of right now, for modules where a live backlog
  count or balance is the more meaningful signal (Inventory pending
  adjustments, HR pending expense approvals, Project pending budget
  approvals, Plant asset book value) or where cumulative-to-date avoids
  fragile date-boundary handling (Quality pass rate, Fleet trip cost).
""",
    "version": "18.0.1.0.0",
    "category": "Reporting",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": [
        "bpro_base",
        "bpro_sales",
        "bpro_manufacturing",
        "bpro_inventory",
        "bpro_finance",
        "bpro_hr",
        "bpro_logistics",
        "bpro_quality",
        "bpro_plant",
        "bpro_project",
        "bpro_fleet",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/executive_dashboard_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "bpro_dashboard/static/src/scss/bpro_dashboard.scss",
        ],
    },
    "installable": True,
    "application": False,
}
