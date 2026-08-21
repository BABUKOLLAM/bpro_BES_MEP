{
    "name": "bpro Department Orders — Indents, Approval & Tracking",
    "summary": "Department indents with HOD approval: stock issue or purchase RFQ, department-wise registers",
    "description": """
One workflow covering the four department-ordering needs ME Polymers
asked for (2026-08-21, "all of the above"):

* Internal material indents - any department raises an order on Stores;
  on HOD approval an internal issue (stock picking to that department's
  consumption location) is created for Stores to validate.
* Purchase requests by department - same document with type Purchase;
  after HOD approval the Purchase team sets a vendor and one click
  creates the draft RFQ, linked back to the indent.
* Department-wise reporting - the indent register itself (list + pivot
  by department/type/state), and a Department field with filters and
  group-by added to Purchase Orders and Inventory Transfers.
* Approval routing by department - the approver is always the ordering
  department's own head (hr.department.manager_id); requesters cannot
  approve their own indents.
""",
    "version": "18.0.1.0.0",
    "category": "Inventory/Purchase",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": ["stock", "purchase", "hr", "mail"],
    "data": [
        "security/dept_order_security.xml",
        "security/ir.model.access.csv",
        "views/bpro_dept_order_views.xml",
        "views/purchase_order_views.xml",
        "views/stock_picking_views.xml",
    ],
    "installable": True,
    "auto_install": False,
}
