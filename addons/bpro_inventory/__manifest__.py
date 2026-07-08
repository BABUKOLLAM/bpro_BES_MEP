{
    "name": "bpro Inventory — Stock Adjustment Approval",
    "summary": "Threshold-gated approval for manual stock adjustments (BES Inventory & Warehouse module)",
    "description": """
Fills the one gap between native Odoo Inventory and the BES BRD's
Inventory & Warehouse Management requirements:

* Every manual stock adjustment requires a reason.
* Adjustments whose value (qty x standard cost) exceeds the per-company bpro.policy threshold 'stock_adjustment_value' are blocked until a Stock Manager approves them (bpro_approval mixin).
* The reason code, before-quantity and after-quantity are stored on the resulting stock.move, so the native stock.move records already are the audit trail required by the BRD - no separate audit table.

Bin-level stock tracking, barcode receive/pick, reordering rules and
allocation/no-oversell are native Odoo Inventory features, enabled via
configuration (Settings > Inventory > Storage Locations, Reordering
Rules) rather than custom code.
""",
    "version": "18.0.1.0.0",
    "category": "Inventory/Inventory",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": ["bpro_base", "bpro_approval", "stock"],
    "data": [
        "views/stock_quant_views.xml",
    ],
    "installable": True,
    "application": False,
}
