import re

from odoo import fields, models
from odoo.exceptions import UserError


class ClientOnboarding(models.TransientModel):
    _name = "bpro.client.onboarding"
    _description = "Client Onboarding Wizard"

    client_name = fields.Char(string="Client Organisation", required=True)
    logo = fields.Binary(string="Client Logo", help="Defaults to the bpro logo if empty.")
    hr_name = fields.Char(string="HR Admin Name", required=True)
    hr_email = fields.Char(string="HR Admin Email (login)", required=True)
    hr_password = fields.Char(string="Initial Password", required=True)
    first_department = fields.Char(
        string="First Department",
        default="General",
        help="Created inside the new company (optional).",
    )
    portal_domain = fields.Char(
        string="Portal Domain",
        help="White-label portal domain, e.g. clientname.bprolms.com. "
        "Leave empty to configure later.",
    )
    street = fields.Char(string="Street")
    street2 = fields.Char(string="Street 2")
    city = fields.Char(string="City")
    state_id = fields.Many2one("res.country.state", string="State")
    zip = fields.Char(string="PIN Code")
    country_id = fields.Many2one(
        "res.country", string="Country", default=lambda self: self.env.ref("base.in")
    )
    phone = fields.Char(string="Company Phone")
    vat = fields.Char(string="GSTIN")
    l10n_in_pan = fields.Char(string="PAN")

    @staticmethod
    def _bpro_warehouse_code(name):
        """stock.warehouse.code is required, alnum, max 5 chars. Unique is
        scoped to (code, company_id), so a same-prefix collision with an
        unrelated company is fine - only sibling companies from very
        similar names could collide, which is an acceptable edge case for
        an auto-derived default the client can rename later."""
        code = re.sub(r"[^A-Za-z0-9]", "", name).upper()[:5]
        return code or "WH"

    def action_onboard(self):
        self.ensure_one()
        master = self.env["res.company"].sudo().search(
            [("parent_id", "=", False)], limit=1, order="id"
        )
        if self.env["res.company"].sudo().search_count(
            [("name", "=", self.client_name)]
        ):
            raise UserError(f"A company named '{self.client_name}' already exists.")
        if self.env["res.users"].sudo().search_count(
            [("login", "=", self.hr_email)]
        ):
            raise UserError(f"A user with login '{self.hr_email}' already exists.")

        company = self.env["res.company"].sudo().create(
            {
                "name": self.client_name,
                "parent_id": master.id,
                "logo": self.logo or master.logo,
                "street": self.street,
                "street2": self.street2,
                "city": self.city,
                "state_id": self.state_id.id,
                "zip": self.zip,
                "country_id": self.country_id.id,
                "phone": self.phone,
                "vat": self.vat,
                "l10n_in_pan": self.l10n_in_pan,
                # Odoo enforces that a company with parent_id set must carry
                # the *exact same* currency_id as its root company (native
                # constraint: res.company._check_root_delegated_fields) -
                # branches can't each bill in a different currency. Set it
                # explicitly to the master's currency rather than relying on
                # res.company.create()'s own default (env.company.currency_id
                # of whichever company happens to be active when the wizard
                # runs), so onboarding never depends on that context.
                "currency_id": master.currency_id.id,
            }
        )
        # the operating super admin must be allowed on the new company
        self.env.user.sudo().write({"company_ids": [(4, company.id)]})

        # native res.company.create() (stock module) sets up transit/
        # inventory-loss/production/scrap locations and sequences for every
        # new company, but does NOT create a stock.warehouse in production -
        # Odoo doesn't assume one warehouse per company. Without this,
        # Inventory, Manufacturing and Purchase are unusable for the new
        # company until someone manually creates a warehouse (discovered
        # live: a fresh company only has an inactive inter-company transit
        # location). Guard with a search: under test runs specifically,
        # that same native create() already provisions one default
        # warehouse per company for test isolation, so this must not
        # duplicate it.
        if not self.env["stock.warehouse"].sudo().search_count(
            [("company_id", "=", company.id)]
        ):
            self.env["stock.warehouse"].sudo().create(
                {
                    "name": self.client_name,
                    "code": self._bpro_warehouse_code(self.client_name),
                    "company_id": company.id,
                    "partner_id": company.partner_id.id,
                }
            )

        department = False
        if self.first_department:
            department = self.env["hr.department"].sudo().create(
                {"name": self.first_department, "company_id": company.id}
            )

        # Client HR Admin is this company's first administrator: also grant
        # manager access to the ERP apps (Sales, Inventory, Purchase,
        # Accounting, HR, Manufacturing, Plant/Maintenance, Project, Fleet)
        # so they can configure their company's setup without a second
        # onboarding step. Scoped to `company` via company_ids above/below -
        # Odoo's native multi-company mechanism, not a new bpro-specific
        # rule. mrp.group_mrp_manager is required separately from
        # maintenance.group_equipment_manager - bpro_plant's Plant &
        # Machinery asset register is ACL-gated on the Manufacturing group,
        # not the Maintenance one (discovered live: the Executive Dashboard's
        # plant asset book value KPI was inaccessible to a client HR Admin
        # without it).
        erp_manager_groups = [
            "sales_team.group_sale_manager",
            "stock.group_stock_manager",
            "purchase.group_purchase_manager",
            "account.group_account_manager",
            "hr.group_hr_manager",
            "mrp.group_mrp_manager",
            "maintenance.group_equipment_manager",
            "project.group_project_manager",
            "fleet.fleet_group_manager",
        ]
        user = self.env["res.users"].sudo().create(
            {
                "name": self.hr_name,
                "login": self.hr_email,
                "email": self.hr_email,
                "password": self.hr_password,
                "company_id": company.id,
                "company_ids": [(6, 0, [company.id])],
                "groups_id": [
                    (4, self.env.ref("base.group_user").id),
                    (4, self.env.ref("bpro_base.group_client_hr").id),
                ]
                + [(4, self.env.ref(xmlid).id) for xmlid in erp_manager_groups],
            }
        )
        # white-label portal: one website per client company (roadmap sec. 4)
        website = self.env["website"].sudo().create(
            {
                "name": f"{self.client_name} Portal",
                "company_id": company.id,
                "domain": self.portal_domain or False,
                "logo": self.logo or master.logo,
            }
        )
        website._bpro_strip_starter_content()

        # employee record triggers global Induction auto-enrollment
        self.env["hr.employee"].sudo().create(
            {
                "name": self.hr_name,
                "company_id": company.id,
                "user_id": user.id,
                "department_id": department and department.id,
                "work_email": self.hr_email,
            }
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "title": "Client onboarded",
                "message": (
                    f"{self.client_name} is live. HR admin {self.hr_email} "
                    "can log in and is enrolled in the global induction."
                ),
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
