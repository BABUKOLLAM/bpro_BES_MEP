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
* Sales commission tracking: per-salesperson commission % (bpro.commission.rate, falling back to a company-wide default policy value), frozen onto the order at confirmation time, with a pivot report by salesperson/period.
* Recurring/subscription orders: an order flagged recurring auto-renews a one-off confirmed copy on its due date via a daily cron, advancing the next renewal date.
* Sales areas (bpro.sales.area): a lightweight territory/district master list, assignable to orders (area-wise sales reporting) and to field sales employees as coverage areas.

Lead capture, pipeline view, quotation generation from price lists/tax, and quotation-to-order conversion are native Odoo CRM/Sales features requiring configuration only. Quotation e-signature (portal_confirmation_sign) and lead source/campaign tracking (utm.mixin on crm.lead) are likewise native - configuration only, no custom code.
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
        "security/bpro_sales_area_multi_company.xml",
        "views/sales_target_views.xml",
        "views/sale_order_views.xml",
        "views/bpro_commission_rate_views.xml",
        "views/sales_area_views.xml",
        "views/hr_employee_views.xml",
        "data/ir_cron.xml",
    ],
    "installable": True,
    "application": False,
}
