#!/usr/bin/env python3
"""First-boot step: put bpro Corporate (the root company) onto India's
GST-mapped chart of accounts with an April-March fiscal year, so every
company onboarded under it (client company currency/fiscal year are
root-delegated fields in Odoo's branch model - see bpro_onboarding) starts
correctly Indian/GST from day one, rather than defaulting to whatever
generic settings a fresh Odoo install picks.

This exists because that setup was done by hand via odoo shell during
development - undocumented, unscripted, and therefore NOT reproduced by a
fresh production database. Run this once, right after first boot's module
install, before onboarding any real client:

    python3 scripts/setup_india_accounting.py https://app.bprolms.com bpro 'MASTER-USER-PASSWORD'

Idempotent: safe to re-run (try_loading no-ops if the company is already on
the "in" template; the company writes are plain field sets). Requires the
root company to have NO existing accounting entries yet (true for a fresh
first-boot database) - Odoo refuses to switch chart templates once any
account.move.line exists for the company, by design.
"""
import sys
import xmlrpc.client

url, db, pwd = sys.argv[1], sys.argv[2], sys.argv[3]
login = sys.argv[4] if len(sys.argv) > 4 else "tech@bpropms.com"
common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
uid = common.authenticate(db, login, pwd, {})
models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")


def call(model, method, *a):
    return models.execute_kw(db, uid, pwd, model, method, list(a))


master_ids = call("res.company", "search", [("parent_id", "=", False)], {"limit": 1, "order": "id"})
if not master_ids:
    sys.exit("no root company found - run the module install step first")
master_id = master_ids[0]

india_ids = call("res.country", "search", [("code", "=", "IN")])
call("res.company", "write", [master_id], {
    "country_id": india_ids[0],
    "fiscalyear_last_day": 31,
    "fiscalyear_last_month": "3",
})
print("root company set to India, fiscal year April-March")

call("account.chart.template", "try_loading", "in", master_id, False)
print("India chart of accounts loaded for the root company")

accounts = call("account.account", "search_count", [("company_ids", "in", [master_id])])
journals = call("account.journal", "search_count", [("company_id", "=", master_id)])
company = call("res.company", "read", [master_id], ["currency_id"])
print(f"verify: {accounts} accounts, {journals} journals, currency={company[0]['currency_id']}")
print("done")
