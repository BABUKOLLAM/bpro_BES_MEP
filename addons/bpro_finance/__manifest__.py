{
    "name": "bpro Finance — Aging, 3-Way Match, Tally Sync, Dashboard",
    "summary": "AR aging, vendor-bill 3-way match approval, Tally XML sync, financial dashboard (BES Finance & Accounts module)",
    "description": """
Fills the gaps between native Odoo Accounting/Purchase and the BES BRD's
Finance & Accounts requirements. This module needed more custom work
than initially planned: this Community image has no account_reports
module (Odoo's Aged Receivable report and Accounting dashboards are
Enterprise-only), so the aging report and financial dashboard below are
built from native ledger fields rather than extending an existing report.

* bpro.ar.aging.wizard: accounts-receivable aging by customer, bucketed current/1-30/31-60/61-90/90+, as of a selected date (FR-FIN-002).
* 3-way match on vendor bills: compares PO ordered qty/price, received qty, and billed qty/price per line, with a per-company configurable tolerance percent; blocks bill approval on mismatch via the bpro_approval mixin (FR-FIN-004).
* Tally XML export/import for sales/purchase/receipt/payment/journal vouchers, with ledger/voucher-type mapping validation and an exceptions report on import (FR-FIN-006/007). Fully custom - no Odoo native equivalent for any edition.
* bpro.finance.dashboard: cash position, total receivables, total payables, and current ratio as of a selected date (FR-FIN-009).
* Financial statement reports - Trial Balance, Balance Sheet, Profit & Loss, Cash Flow Statement (indirect method), and Fund Flow Statement - built from native ledger balances since Community has no account_reports module. Each of the Cash Flow and Fund Flow reports includes a built-in reconciliation check line that must equal zero, since both are independently derivable from the balance sheet identity.

Invoice generation from a confirmed sales order and payment registration (full/partial, with automatic invoice status transitions) are native Odoo Accounting features requiring no custom code.
""",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": ["bpro_base", "bpro_approval", "account", "purchase"],
    "data": [
        "security/ir.model.access.csv",
        "security/bpro_finance_multi_company.xml",
        "views/ar_aging_views.xml",
        "views/finance_dashboard_views.xml",
        "views/financial_reports_views.xml",
        "views/account_move_views.xml",
        "views/tally_views.xml",
        "views/tally_upload_templates.xml",
    ],
    "installable": True,
    "application": False,
}
