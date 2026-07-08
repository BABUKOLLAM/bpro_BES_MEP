{
    "name": "bpro Inventory — Stock Adjustment Approval",
    "summary": "Threshold-gated approval for manual stock adjustments (BES Inventory & Warehouse module)",
    "description": """
Fills the gaps between native Odoo Inventory and the BES BRD's
Inventory & Warehouse Management requirements:

* Every manual stock adjustment requires a reason.
* Adjustments whose value (qty x standard cost) exceeds the per-company bpro.policy threshold 'stock_adjustment_value' are blocked until a Stock Manager approves them (bpro_approval mixin).
* The reason code, before-quantity and after-quantity are stored on the resulting stock.move, so the native stock.move records already are the audit trail required by the BRD - no separate audit table.
* Auto-calculated reorder levels: native reordering rules (product_min_qty/
  product_max_qty) are purely static - there is no built-in way to derive
  them from historical demand. Adds a suggested min/max per orderpoint,
  computed from actual outbound flow over a configurable lookback window
  (customer deliveries for products sold directly, raw-material
  consumption in manufacturing for BOM components, added together), plus
  an "Apply Suggested Levels" button - a deliberate action, not an
  automatic overwrite.

Bin-level stock tracking, barcode receive/pick, and allocation/no-oversell
are native Odoo Inventory features, enabled via configuration (Settings >
Inventory > Storage Locations) rather than custom code.
""",
    "version": "18.0.1.0.0",
    "category": "Inventory/Inventory",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": ["bpro_base", "bpro_approval", "stock", "mrp"],
    "data": [
        "views/stock_quant_views.xml",
        "views/stock_warehouse_orderpoint_views.xml",
    ],
    "installable": True,
    "application": False,
}
