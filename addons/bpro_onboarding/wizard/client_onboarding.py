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
            }
        )
        # the operating super admin must be allowed on the new company
        self.env.user.sudo().write({"company_ids": [(4, company.id)]})

        department = False
        if self.first_department:
            department = self.env["hr.department"].sudo().create(
                {"name": self.first_department, "company_id": company.id}
            )

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
                ],
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
