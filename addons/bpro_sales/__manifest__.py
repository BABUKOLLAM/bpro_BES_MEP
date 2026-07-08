{
    "name": "bpro Sales — CRM & Order Confirmation Gaps",
    "summary": "Duplicate-lead detection, discount approval, credit/stock confirmation blocks, sales target vs actual (BES Sales & CRM module)",
    "description": """
Fills the gaps between native Odoo Sales/CRM and the BES BRD's Sales & CRM requirements:

* Duplicate-lead detection by email/phone within a company, blocking save (FR-SAL-002). Native Odoo CRM has no such check.
* Discount-approval routing: quotations with a line discount above the per-company bpro.policy threshold are blocked from being sent or confirmed until a Sales Manager approves (FR-SAL-008, via the bpro_approval mixin).
* Hard block on order confirmation when the customer's credit limit is exceeded (FR-SAL-010). Native Odoo only shows a non-blocking warning (partner_credit_warning) - this reuses that same computed message but actually enforces it.
* Hard block on order confirmation when ordered quantity exceeds free-to-use stock (FR-SAL-010). Not present natively - Odoo allows confirming orders it can't currently fulfil and backorders them instead.
* bpro.sales.target: target vs. actual attainment per salesperson per period (FR-SAL-012), compared against confirmed sale.order totals.

Lead capture, pipeline view, quotation generation from price lists/tax, and quotation-to-order conversion are native Odoo CRM/Sales features requiring configuration only.
""",
    "version": "18.0.1.0.0",
    "category": "Sales/CRM",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": ["bpro_base", "bpro_approval", "sale_management", "crm"],
    "data": [
        "security/ir.model.access.csv",
        "security/sales_target_security.xml",
        "views/sales_target_views.xml",
    ],
    "installable": True,
    "application": False,
}
