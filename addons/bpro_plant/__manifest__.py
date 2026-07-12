{
    "name": "bpro Plant & Machinery",
    "summary": "Equipment-workcenter linking with maintenance downtime visibility, plus a from-scratch fixed-asset register and depreciation schedule (BES Plant & Machinery module)",
    "description": """
Two angles, two very different levels of native support:

* Equipment & maintenance: Odoo's native maintenance app (equipment
  register, MTBF/MTTR, preventive/corrective requests) is present and
  installed here, but has no link to mrp.workcenter at all - the Enterprise
  bridge module for that doesn't exist in this Community image. Adds
  maintenance.equipment.workcenter_id, a maintenance-downtime warning on
  mrp.workorder when its work center's equipment has an open corrective
  request, and a downtime-hours report by equipment.
* Asset register & depreciation: there is no fixed-asset accounting app at
  all in this image (Enterprise-only, same situation as Payroll and
  Quality) - built from scratch. bpro.plant.asset tracks acquisition cost,
  useful life and salvage value; confirming an asset generates its full
  straight-line depreciation schedule (bpro.plant.asset.depreciation.line);
  a daily cron posts due lines as account.move journal entries (debit
  depreciation expense, credit accumulated depreciation), the same
  cron-based generation shape already used for subscription billing and
  recurring sales orders elsewhere in this codebase.
""",
    "version": "18.0.1.0.0",
    "category": "Manufacturing/Plant & Machinery",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": ["bpro_base", "maintenance", "mrp", "account"],
    "data": [
        "security/ir.model.access.csv",
        "security/bpro_plant_multi_company.xml",
        "views/maintenance_equipment_views.xml",
        "views/mrp_workorder_views.xml",
        "views/bpro_plant_asset_views.xml",
        "data/ir_cron.xml",
    ],
    "installable": True,
    "application": False,
}
