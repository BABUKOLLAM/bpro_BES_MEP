{
    "name": "bpro Field Sales — Journey Plan & Collection Plan",
    "summary": "Field sales rep visit planning and dealer/distributor collection planning",
    "description": """
For field sales & marketing staff visiting dealers/distributors across
their assigned area:

* bpro.field.journey.plan: a planned schedule of dealer/distributor
  visits per salesperson (date, purpose), marked Visited or Missed with
  outcome notes on return - no native Field Service equivalent exists
  in this Community image (it's Enterprise-only and built for on-site
  service technicians, not repeat sales-rep dealer visits), so this is
  a small purpose-built model.
* bpro.field.collection.plan: a planned schedule to collect outstanding
  dues from a dealer/distributor (expected amount, target date), against
  their live outstanding balance (native res.partner.credit), recorded
  as Collected/Partially Collected/Missed with the actual amount
  received.
* Claim submission for field staff travel/visit expenses already exists
  natively via the Expenses app (with bpro_hr's Finance-approval
  threshold gate) - no new model needed there.
""",
    "version": "18.0.1.0.0",
    "category": "Sales/CRM",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": ["bpro_base", "crm", "account"],
    "data": [
        "security/ir.model.access.csv",
        "security/bpro_field_sales_multi_company.xml",
        "views/bpro_field_journey_plan_views.xml",
        "views/bpro_field_collection_plan_views.xml",
    ],
    "installable": True,
    "application": False,
}
