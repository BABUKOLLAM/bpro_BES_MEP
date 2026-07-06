{
    "name": "bpro Billing — Client Subscriptions",
    "summary": "Per-seat subscription billing for client organisations (roadmap P7)",
    "description": """
Subscription billing for the bpro LMS + PMS SaaS:
* Plans with per-seat monthly/yearly pricing
* One subscription per client company, seat count = active employees
* Daily cron raises draft invoices on the renewal date
""",
    "version": "18.0.1.0.0",
    "category": "Sales/Subscriptions",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": ["bpro_base", "bpro_pms", "account"],
    "data": [
        "security/ir.model.access.csv",
        "data/billing_cron.xml",
        "views/billing_views.xml",
    ],
    "installable": True,
    "application": False,
}
