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

Weekly MIS section: reproduces the client's own hand-maintained weekly
production/sales meeting report from live data instead of a spreadsheet
rebuilt every week - week-over-week and month-over-month trend on
production qty and sales value, item-wise production achieved/target/
balance (against bpro.item.target), item-wise weekly sales achieved/
target, and area-wise sales load counts (against bpro.sales.area, from
bpro_sales).
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
        "security/bpro_item_target_multi_company.xml",
        "views/executive_dashboard_views.xml",
        "views/item_target_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "bpro_dashboard/static/src/scss/bpro_dashboard.scss",
        ],
    },
    "installable": True,
    "application": False,
}
