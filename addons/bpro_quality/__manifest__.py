{
    "name": "bpro Quality — Quality Management",
    "summary": "Quality checkpoints blocking receipt and manufacturing completion (BES Quality Management module)",
    "description": """
There is no Quality/QC app at all in this Odoo Community image (Quality is
Enterprise-only, and its code isn't bundled here) - unlike every other BES
module, this one has no native foundation to configure or extend, and is
built from scratch.

* bpro.quality.point: a checkpoint definition (which product or product
  category, which operation - incoming receipt or manufacturing,
  instructions).
* bpro.quality.check: the pass/fail record, auto-created when a receipt
  (stock.picking) or work order (mrp.workorder) reaches completion and a
  matching quality point exists.
* Hard block: a receipt or work order cannot be marked done while any of
  its quality checks are still pending or failed - the same hard-block
  shape already used for the stock-shortage and discount-approval gates
  elsewhere in this codebase.
* A pass/fail rate report by product.
""",
    "version": "18.0.1.0.0",
    "category": "Manufacturing/Quality",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": ["bpro_base", "stock", "mrp", "purchase_stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/bpro_quality_point_views.xml",
        "views/bpro_quality_check_views.xml",
    ],
    "installable": True,
    "application": False,
}
