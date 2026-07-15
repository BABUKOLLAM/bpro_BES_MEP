#!/usr/bin/env python3
"""Pre-launch cleanup: remove the dummy/demo data seeded across every custom
module for ME Polymers Private Limited (used to walk through the whole
platform before go-live). Deletes exactly the records listed in
me_polymers_demo_data_manifest.json, in reverse-creation order (children
before parents), and nothing else.

Run from the repo root:

    python3 scripts/remove_me_polymers_demo_data.py https://app.bprolms.com bpro 'MASTER-USER-PASSWORD'

Two records referenced by the demo data are deliberately NOT in the manifest
because they are real, pre-existing master data (not created by the seed
run) and must never be deleted: hr.department "Production" and the
product.template "SPARK SHEET". The demo run only added stock/BOM
references to them.
"""
import json
import os
import sys
import xmlrpc.client

MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "me_polymers_demo_data_manifest.json")

url, db, pwd = sys.argv[1], sys.argv[2], sys.argv[3]
login = sys.argv[4] if len(sys.argv) > 4 else "tech@bpropms.com"

with open(MANIFEST_PATH) as f:
    records = json.load(f)

common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
uid = common.authenticate(db, login, pwd, {})
models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

def call(model, method, *a):
    return models.execute_kw(db, uid, pwd, model, method, list(a))

deleted, skipped = 0, 0
for model, res_id in reversed(records):
    try:
        existing = call(model, "search", [("id", "=", res_id)])
        if not existing:
            skipped += 1
            continue
        call(model, "unlink", existing)
        deleted += 1
    except Exception as e:
        print(f"  could not delete {model}({res_id}): {e}")
        skipped += 1

print(f"deleted {deleted} demo records, skipped {skipped} (already gone or blocked by a reference)")
print("verify under ME Polymers Private Limited: Employees, Contacts, Sales, Inventory, Manufacturing, Accounting, Helpdesk, Projects, Fleet, Field Sales, PMS")
