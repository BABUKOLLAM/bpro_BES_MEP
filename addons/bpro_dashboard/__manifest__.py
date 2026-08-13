{
    "name": "bpro Executive Dashboard",
    "summary": "One-glance cross-module KPI dashboard tying together all 11 BES modules",
    "description": """
A capstone reporting layer, not a new operational module - pulls one
primary KPI from each BES module already built into a single screen,
reusing each module's own existing computation rather than duplicating
logic (the Finance section calls straight into
bpro.finance.dashboard's own _get_kpi_data).

Blends two kinds of signal deliberately:
* "Flow" metrics scoped to month-to-date, for modules with a clean
  business date (Sales revenue, Manufacturing output variance,
  Logistics on-time delivery %).
* "Stock" metrics read as of right now, for modules where a live backlog
  count or balance is the more meaningful signal (Inventory pending
  adjustments, HR pending expense approvals, Project pending budget
  approvals, Plant asset book value, Recruitment open vacancies/overdue
  joining reports) or where cumulative-to-date avoids fragile date-
  boundary handling (Quality pass rate, Fleet trip cost).

Weekly MIS section: reproduces the client's own hand-maintained weekly
production/sales meeting report from live data instead of a spreadsheet
rebuilt every week - week-over-week and month-over-month trend on
production qty and sales value, item-wise production achieved/target/
balance (against bpro.item.target), item-wise weekly sales achieved/
target, and area-wise sales load counts (against bpro.sales.area, from
bpro_sales).

Recruitment (R4.6): pulls two management-facing signals from
bpro_recruitment - open vacancies still short of their target headcount
(approved bpro.vacancy.request whose linked hr.job isn't fully hired)
and overdue joining reports (pending bpro.joining.report past their SLA
deadline) - the "shareable to management for review" half of the
original requirement; the HOD-facing half is department-scoped
read-only access on bpro_recruitment's own models, not a dashboard
concern.

HR analytics (post-R5.3): pending attendance exceptions (unexplained
absences awaiting HR review, from bpro_attendance), open exit requests
(in-flight separations, from bpro_exit), trailing-12-month attrition
rate (closed exits over current active headcount), and Earned Leave
encashment liability (every active employee's EL balance x Basic/26 -
the same s79(11) formula bpro_exit's F&F uses, so the dashboard
liability figure and an actual settlement always agree).
""",
    "version": "18.0.1.2.0",
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
        "bpro_recruitment",
        "bpro_attendance",
        "bpro_exit",
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
