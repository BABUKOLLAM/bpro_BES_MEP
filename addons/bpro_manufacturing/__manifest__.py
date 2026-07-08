{
    "name": "bpro Manufacturing — Operator Capture & Output Reporting",
    "summary": "Unified reject capture, capacity-conflict warning, actual-vs-planned reporting (BES Manufacturing & Production Planning module)",
    "description": """
Fills the gaps between native Odoo Manufacturing and the BES BRD's
Manufacturing & Production Planning requirements:

* Unified operator capture: completed and rejected quantity plus a reject reason in one step (FR-MFG-005). Native Odoo tracks produced quantity on the work order but rejects only via a separate stock.scrap record with no reason prompt and no cumulative rejected-quantity field on the work order itself.
* Non-blocking capacity-conflict warning when a work order is manually rescheduled onto a work center slot that's already fully booked (FR-MFG-002). Native manual reschedule recomputes duration but doesn't flag an overlap the way the automated Plan button's scheduler does.
* Actual vs. planned output variance (qty and %) computed directly on mrp.workorder, with a pivot report by work order/work center for a date range (FR-MFG-009). Not present natively - existing MRP reports are cost/BOM-structure focused, not planned-vs-actual output.

Capacity-aware work order scheduling (the Plan button), BOM/routing work order generation, BOM-aware MRP netting through the Replenishment view, and forward/backward lot genealogy trace are native Odoo Manufacturing/Inventory features requiring configuration only.
""",
    "version": "18.0.1.0.0",
    "category": "Manufacturing",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": ["bpro_base", "mrp"],
    "data": [
        "views/mrp_workorder_views.xml",
    ],
    "installable": True,
    "application": False,
}
