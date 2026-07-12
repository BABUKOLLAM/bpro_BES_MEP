{
    "name": "bpro Helpdesk — Customer Support",
    "summary": "Ticketing with SLA tracking, closing the loop after Sales (BES Helpdesk / Customer Support module)",
    "description": """
Unlike every other BES module built on top of a native Odoo app, there is
no Helpdesk app at all in this Odoo Community image (Enterprise-only,
same situation as Payroll, Quality, and Fixed Assets) - this module is
built from scratch.

* bpro.helpdesk.stage: simple kanban stages (New / In Progress / Resolved
  / Closed) with an is_closed flag, the same shape already used for
  maintenance.stage.
* bpro.helpdesk.team: a lightweight team grouping (name + members).
* bpro.helpdesk.ticket: subject, customer, description, priority, team/
  assignee, an optional link to the originating sale.order (closing the
  loop with Sales - a customer's support history is visible from their
  record), an SLA deadline computed from ticket creation plus a
  per-company response-time policy (bpro.policy), a non-blocking overdue
  flag, and resolution time captured once closed.
* An SLA compliance report: ticket volume, overdue count and average
  resolution time by team.
""",
    "version": "18.0.1.0.0",
    "category": "Services/Helpdesk",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": ["bpro_base", "bpro_approval", "mail", "sale"],
    "data": [
        "security/ir.model.access.csv",
        "security/bpro_helpdesk_multi_company.xml",
        "data/helpdesk_stage_data.xml",
        "views/helpdesk_ticket_views.xml",
        "views/helpdesk_team_views.xml",
        "views/helpdesk_stage_views.xml",
    ],
    "installable": True,
    "application": True,
}
