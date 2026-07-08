{
    "name": "bpro Project — Budget Overrun Approval & Workload Visibility",
    "summary": "Threshold-gated task budget-overrun approval, plus employee cross-project workload warning (BES Project Management module)",
    "description": """
Fills two gaps between native Odoo Project Management (project, hr_timesheet,
sale_timesheet) and a BES-style Project Management module.

* Task budget-overrun approval: project.task has allocated_hours and a
  computed effective_hours (time actually logged), but nothing blocks a
  task from being closed once logged hours exceed the allocation - the
  same threshold-gate shape used for sales discounts, vendor-bill 3-way
  match, and expense approval elsewhere in this codebase. A task whose
  overrun exceeds a per-company bpro.policy percentage cannot move to a
  closed state until a Project Manager approves it.
* Employee cross-project workload warning: there is no native check for
  an employee being over-committed across their open tasks (Community
  edition has no Gantt-style planned date range on tasks to check true
  schedule overlap, only a single deadline) - a non-blocking warning
  compares the sum of allocated_hours across all of an assigned employee's
  currently open tasks against a configurable capacity threshold.

Task/project management, timesheets, milestones (project.milestone), and
profitability tracking (task rate / fixed rate / employee rate pricing)
are native Odoo features requiring configuration only.
""",
    "version": "18.0.1.0.0",
    "category": "Services/Project",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": ["bpro_base", "bpro_approval", "project", "hr_timesheet", "sale_timesheet"],
    "data": [
        "views/project_task_views.xml",
    ],
    "installable": True,
    "application": False,
}
