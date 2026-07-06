#!/usr/bin/env python3
"""Pre-launch cleanup: deactivate the local test users and demo client
companies. Review the lists below, then run:

    python3 scripts/remove_test_data.py https://app.bprolms.com bpro 'MASTER-USER-PASSWORD'

Archives (does not delete) so nothing is lost if run by mistake.
"""
import sys
import xmlrpc.client

TEST_LOGINS = [
    "hr.a@test", "hod.a@test", "emp.a@test", "hr.b@test",
    "new.emp@test", "hr@myg.test", "hr@bella.test",
]
TEST_COMPANIES = [
    "Client A Pvt Ltd", "Client B Pvt Ltd",
    "myG Digital Pvt Ltd", "Bella Malaysia Sdn Bhd",
]

url, db, pwd = sys.argv[1], sys.argv[2], sys.argv[3]
login = sys.argv[4] if len(sys.argv) > 4 else "tech@bpropms.com"
common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
uid = common.authenticate(db, login, pwd, {})
models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
def call(model, method, *a):
    return models.execute_kw(db, uid, pwd, model, method, list(a))

users = call("res.users", "search", [("login", "in", TEST_LOGINS)])
call("res.users", "write", users, {"active": False})
print(f"archived {len(users)} test users")

emps = call("hr.employee", "search", [("company_id.name", "in", TEST_COMPANIES)])
call("hr.employee", "write", emps, {"active": False})
companies = call("res.company", "search", [("name", "in", TEST_COMPANIES)])
call("res.company", "write", companies, {"active": False})
print(f"archived {len(emps)} employees and {len(companies)} test companies")
print("done — verify in Settings > Companies and Settings > Users")
