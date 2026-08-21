# Best-effort default grouping for ME Polymers' current app roster, mapped
# 2026-08-12 from the flat apps-switcher list into Sales/Production/
# Accounts/HR/General. Keyed by each app's own root-menu external ID so
# this survives module renames on our side but still resolves correctly
# against upstream/OCA addons. Every lookup below is optional
# (raise_if_not_found=False) - this module has no hard manifest dependency
# on any of the apps being grouped, so a client without e.g. Fleet or
# Purchase installed just skips those two lines instead of failing.
_MENU_GROUP_ASSIGNMENTS = {
    # Sales (incl. outbound marketing - customer-facing function)
    "crm.crm_menu_root": "menu_group_sales",
    "sale.sale_menu_root": "menu_group_sales",
    "mass_mailing.mass_mailing_menu_root": "menu_group_sales",
    "utm.menu_link_tracker_root": "menu_group_sales",
    # Production (manufacturing + the supply chain that feeds it)
    "mrp.menu_mrp_root": "menu_group_production",
    "stock.menu_stock_root": "menu_group_production",
    "purchase.menu_purchase_root": "menu_group_production",
    "fleet.menu_root": "menu_group_production",
    "maintenance.menu_maintenance_title": "menu_group_production",
    # Accounts
    "account.menu_finance": "menu_group_accounts",
    "hr_expense.menu_hr_expense_root": "menu_group_accounts",
    # HR - the full people lifecycle, incl. self-service, hiring,
    # learning and performance (2026-08-16 reorganisation, per client)
    "hr.menu_hr_root": "menu_group_hr",
    "hr_holidays.menu_hr_holidays_root": "menu_group_hr",
    "hr_attendance.menu_hr_attendance_root": "menu_group_hr",
    "hr_timesheet.timesheet_menu_root": "menu_group_hr",
    "hr_recruitment.menu_hr_recruitment_root": "menu_group_hr",
    "payroll.payroll_menu_root": "menu_group_hr",
    "bpro_ess.menu_bpro_ess_root": "menu_group_hr",
    "website_slides.website_slides_menu_root": "menu_group_hr",
    "bpro_pms.menu_pms_root": "menu_group_hr",
    # Productivity - cross-department work and collaboration tools
    "project_todo.menu_todo_todos": "menu_group_productivity",
    "calendar.mail_menu_calendar": "menu_group_productivity",
    "contacts.menu_contacts": "menu_group_productivity",
    "mail.menu_root_discuss": "menu_group_productivity",
    "im_livechat.menu_livechat_root": "menu_group_productivity",
    "survey.menu_surveys": "menu_group_productivity",
    "project.menu_main_pm": "menu_group_productivity",
    "bpro_helpdesk.menu_bpro_helpdesk_root": "menu_group_productivity",
    "spreadsheet_dashboard.spreadsheet_dashboard_menu_root": "menu_group_productivity",
    "bpro_data_tools.menu_bpro_data_upload_root": "menu_group_productivity",
    "website.menu_website_configuration": "menu_group_productivity",
    # General - the fallback keeps only what every user reaches for
    # (Executive Dashboard) plus admin entries (Apps, Settings)
    "bpro_dashboard.menu_bpro_executive_dashboard_root": "menu_group_general",
}


def assign_default_menu_groups(env):
    for menu_xmlid, group_xmlid in _MENU_GROUP_ASSIGNMENTS.items():
        menu = env.ref(menu_xmlid, raise_if_not_found=False)
        group = env.ref(f"bpro_navigation.{group_xmlid}", raise_if_not_found=False)
        if menu and group:
            menu.bpro_group_id = group.id
