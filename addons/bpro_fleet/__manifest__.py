{
    "name": "bpro Fleet — Owned vs. Hired/External Vehicles",
    "summary": "Ownership type, transporter linking, and trip billing for hired vehicles (BES Fleet Management module)",
    "description": """
Fills the gap between native Odoo Fleet (fleet, stock_fleet) and a
BES-style Fleet Management module covering both owned and external vehicles.

stock_fleet already links fleet.vehicle to stock.picking.batch (assigns a
vehicle + driver to a delivery run, checks weight/volume against the
vehicle model) - that covers owned-vehicle dispatch almost entirely
natively. But fleet.vehicle has no concept of ownership at all: every
vehicle is modeled as if it's permanently the company's own, with no way
to represent a one-off hired/external vehicle, its transporter, or its
per-trip cost.

* fleet.vehicle: an ownership type (Owned / Hired-External), a linked
  transporter vendor and a default trip rate + expense account, required
  only for hired vehicles.
* stock.picking.batch: a trip cost (defaulting from the vehicle's rate)
  and a "Create Transporter Bill" button that generates a vendor bill to
  the transporter once a hired-vehicle batch is done - not automatic,
  since billing a transporter is a deliberate action, not a background job.
* A fleet cost report comparing owned vs. hired vehicle trip costs.
""",
    "version": "18.0.1.0.0",
    "category": "Inventory/Fleet",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": ["bpro_base", "fleet", "stock_fleet", "account"],
    "data": [
        "views/fleet_vehicle_views.xml",
        "views/stock_picking_batch_views.xml",
    ],
    "installable": True,
    "application": False,
}
