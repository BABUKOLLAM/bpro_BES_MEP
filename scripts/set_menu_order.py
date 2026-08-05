"""Reorders the top-level Apps switcher (the grid icon in the navbar) so
the modules ME Polymers actually runs the business on come first, in the
same priority order the homepage itself states (Sales & CRM, Production,
Inventory, Finance, HR & Admin, Fleet & Logistics), with generic Odoo
collaboration/utility apps (Discuss, Calendar, To-do, Contacts, Website,
spreadsheet Dashboards) pushed to the bottom.

This is a per-deployment preference, not generic platform behavior - a
different bpro client might want a different priority order - so it's a
standalone script (like setup_india_accounting.py), not baked into an
addon's data files. Baking it into an addon would also force that addon
to depend on every app referenced below (crm, sale, mrp, stock, account,
purchase, hr, fleet, project, ...), which isn't worth it for a one-time
ordering tweak.

Only sets `sequence` on each app's EXISTING root menu record - no menus
created, renamed, or removed. Uses raise_if_not_found=False throughout so
it degrades gracefully on a deployment that doesn't have every app
installed (e.g. no Fleet, no Maintenance).

Idempotent: safe to re-run any time the app list changes.

Run via odoo shell (not XML-RPC, for consistency with the other one-off
scripts in this directory - no technical requirement here, just
consistency):

    docker compose -f deploy/docker-compose.prod.yml exec -i odoo \\
      /entrypoint.sh odoo shell -c /etc/odoo/odoo.conf -d bpro --no-http \\
      < scripts/set_menu_order.py
"""

MENU_SEQUENCE = {
    "bpro_dashboard.menu_bpro_executive_dashboard_root": 5,
    "crm.crm_menu_root": 10,
    "sale.sale_menu_root": 15,
    "mrp.menu_mrp_root": 20,
    "stock.menu_stock_root": 25,
    "account.menu_finance": 30,
    "purchase.menu_purchase_root": 35,
    "hr.menu_hr_root": 40,
    "hr_holidays.menu_hr_holidays_root": 45,
    "hr_expense.menu_hr_expense_root": 50,
    "hr_attendance.menu_hr_attendance_root": 55,
    "fleet.menu_root": 60,
    "bpro_helpdesk.menu_bpro_helpdesk_root": 65,
    "project.menu_main_pm": 70,
    "bpro_pms.menu_pms_root": 75,
    "hr_timesheet.timesheet_menu_root": 80,
    "website_slides.website_slides_menu_root": 85,
    "maintenance.menu_maintenance_title": 90,
    "im_livechat.menu_livechat_root": 95,
    "spreadsheet_dashboard.spreadsheet_dashboard_menu_root": 100,
    "website.menu_website_configuration": 105,
    "calendar.mail_menu_calendar": 110,
    "project_todo.menu_todo_todos": 115,
    "contacts.menu_contacts": 120,
    "mail.menu_root_discuss": 125,
}

applied, skipped = [], []
for xmlid, sequence in MENU_SEQUENCE.items():
    menu = env.ref(xmlid, raise_if_not_found=False)
    if menu:
        menu.sequence = sequence
        applied.append(xmlid)
    else:
        skipped.append(xmlid)

env.cr.commit()
print(f"applied: {len(applied)} menus reordered")
if skipped:
    print(f"skipped (not installed on this deployment): {skipped}")
