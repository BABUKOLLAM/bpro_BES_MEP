{
    "name": "bpro Logistics — Supply Chain Gaps",
    "summary": "Vendor on-time-delivery performance tracking (BES Logistics & Supply Chain module)",
    "description": """
Fills the gap between native Odoo purchasing/inventory and a BES-style
Logistics & Supply Chain module.

* Vendor performance tracking: native purchase.report only has a static
  configured lead-time metric ("Days to Receive", computed from
  date_planned - date_order, i.e. the promised lead time) - there is no
  comparison of a receipt's ACTUAL arrival date against what was promised.
  This addon adds bpro_on_time/bpro_delay_days on stock.picking, computed
  when an incoming receipt linked to a purchase.order is validated, plus a
  vendor scorecard report (on-time %, average delay) grouped by vendor.

Vendor agreements/RFQ comparison (purchase_requisition), landed costs
(stock_landed_costs), and batch/wave picking (stock_picking_batch) are
native Odoo features requiring configuration only.
""",
    "version": "18.0.1.0.0",
    "category": "Inventory/Purchase",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": [
        "bpro_base",
        "purchase",
        "stock",
        "purchase_requisition",
        "stock_landed_costs",
        "stock_picking_batch",
    ],
    "data": [
        "views/stock_picking_views.xml",
    ],
    "installable": True,
    "application": False,
}
