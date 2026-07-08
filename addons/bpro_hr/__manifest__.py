{
    "name": "bpro HR — Employee Lifecycle & Expense Approval Gaps",
    "summary": "Departure deactivates the linked user login; threshold-gated Finance approval for expense claims (BES HR & Payroll module)",
    "description": """
Fills the gaps between native Odoo HR (hr_contract, hr_holidays, hr_attendance,
hr_expense) and a BES-style HR & Payroll module. Payroll itself is out of
scope: no payroll app exists at all in this Odoo Community image (Odoo's own
Payroll is Enterprise-only) - deferred as its own, larger scoping
conversation rather than bundled into this pass.

* Registering an employee's departure now also deactivates their linked
  res.users login. Native Odoo's departure wizard only sets
  departure_reason_id/departure_date and archives the hr.employee record -
  it never touches the user account, leaving an offboarded employee's login
  active indefinitely. A real gap in a multi-tenant platform built around
  access security (bpro_base).
* Expense claims above a per-company bpro.policy threshold
  (hr_expense_finance_approval_pct) require Finance Manager approval in
  addition to the direct manager's native approval - the same threshold-gate
  shape used for sales discounts and vendor-bill 3-way match, applied by
  hand here (not via bpro.approval.mixin) since hr.expense.sheet already has
  its own native approval_state field of a different shape (submit/approve/
  cancel, feeding _compute_state) - reusing the mixin's field name would
  silently redefine those selection values and break native state
  computation.

Employee records, departments, contracts (with native expiry reminders),
leave/time-off (with native manager/HR/double validation and negative-cap
allowances), and attendance are native Odoo HR features requiring
configuration only.
""",
    "version": "18.0.1.0.0",
    "category": "Human Resources",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": [
        "bpro_base",
        "bpro_approval",
        "hr_contract",
        "hr_holidays",
        "hr_attendance",
        "hr_expense",
    ],
    "data": [
        "views/hr_expense_sheet_views.xml",
    ],
    "installable": True,
    "application": False,
}
