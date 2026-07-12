{
    "name": "bpro Collections — Dues Follow-up & Escalation",
    "summary": "Per-customer overdue-receivable tracking with escalation levels and follow-up scheduling",
    "description": """
Odoo's native payment-reminder/dunning workflow (account_followup) is
Enterprise-only and not bundled in this Community image - this addon is
a from-scratch equivalent, one case per customer with an overdue
balance:

* bpro.collections.case: overdue amount and oldest overdue date are
  computed live from unreconciled posted receivable lines (same query
  bpro_finance's AR Aging report already uses), rolled up to an
  escalation level (Reminder/Firm/Final) driven by configurable
  bpro.policy day thresholds.
* A nightly cron keeps cases in sync: opens a case for any customer who
  newly has overdue receivables, and auto-closes any case whose balance
  has been cleared - no manual bookkeeping.
* Recording a contact (call/visit/reminder sent) schedules the next
  follow-up date automatically from a configurable interval.

Complements (not a duplicate of) bpro_field_sales' Collection Plan: this
is the company-wide, invoice-driven aging tracker; the Collection Plan
is a field rep's own planned visit-by-visit collection schedule.
""",
    "version": "18.0.1.0.0",
    "category": "Accounting/Accounting",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": ["bpro_base", "bpro_approval", "account"],
    "data": [
        "security/ir.model.access.csv",
        "security/bpro_collections_multi_company.xml",
        "views/bpro_collections_case_views.xml",
        "data/ir_cron.xml",
    ],
    "installable": True,
    "application": False,
}
