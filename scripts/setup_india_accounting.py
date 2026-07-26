"""First-boot step: put the root company onto India's GST-mapped chart of
accounts with an April-March fiscal year, so every company onboarded under
it (client company currency/fiscal year are root-delegated fields in
Odoo's branch model - see bpro_onboarding) starts correctly Indian/GST
from day one, rather than defaulting to whatever generic settings a fresh
Odoo install picks.

This exists because that setup was done by hand via odoo shell during
development - undocumented, unscripted, and therefore NOT reproduced by a
fresh production database. Run this once, right after first boot's module
install, before onboarding any real client.

Must run inside `odoo shell`, not over XML-RPC: account.chart.template's
try_loading() returns None, and Odoo's XML-RPC endpoint hard-codes
allow_none=False server-side, so any XML-RPC client (regardless of how the
call is built) gets an unmarshallable-response error. Run it like this:

    docker compose -f deploy/docker-compose.prod.yml exec -i odoo \\
      /entrypoint.sh odoo shell -c /etc/odoo/odoo.conf -d bpro --no-http \\
      < scripts/setup_india_accounting.py

Idempotent: safe to re-run (try_loading no-ops if the company is already on
the "in" template; the company writes are plain field sets). Requires the
root company to have NO existing accounting entries yet (true for a fresh
first-boot database) - Odoo refuses to switch chart templates once any
account.move.line exists for the company, by design.
"""

company = env['res.company'].search([('parent_id', '=', False)], limit=1, order='id')
if not company:
    raise SystemExit("no root company found - run the module install step first")

india = env['res.country'].search([('code', '=', 'IN')], limit=1)
company.write({
    'country_id': india.id,
    'fiscalyear_last_day': 31,
    'fiscalyear_last_month': '3',
})
print("root company set to India, fiscal year April-March")

env['account.chart.template'].with_company(company).try_loading('in', company, install_demo=False)
env.cr.commit()
print("India chart of accounts loaded for the root company")

accounts = env['account.account'].search_count([('company_ids', 'in', company.id)])
journals = env['account.journal'].search_count([('company_id', '=', company.id)])
print(f"verify: {accounts} accounts, {journals} journals, "
      f"chart_template={company.chart_template}, currency={company.currency_id.name}")
print("done")
