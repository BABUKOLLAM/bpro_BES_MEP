from odoo import api, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    @api.model_create_multi
    def create(self, vals_list):
        employees = super().create(vals_list)
        employees._enroll_tagged_courses("bpro_lms.tag_induction")
        return employees

    def _lms_partner(self):
        self.ensure_one()
        return self.user_id.partner_id or self.work_contact_id

    def _lms_partners(self):
        partners = self.env["res.partner"]
        for emp in self:
            partner = emp._lms_partner()
            if partner:
                partners |= partner
        return partners

    def _visible_courses_domain(self):
        self.ensure_one()
        return [
            "|",
            ("company_id", "=", False),
            ("company_id", "parent_of", [self.company_id.id]),
        ]

    def _enroll_tagged_courses(self, tag_xmlid, reset=False):
        """Enroll employees into every visible course carrying the tag.
        With reset=True existing memberships are removed first, so
        completion starts over (used for annual Re-Induction)."""
        tag = self.env.ref(tag_xmlid, raise_if_not_found=False)
        if not tag:
            return
        Channel = self.env["slide.channel"].sudo()
        Membership = self.env["slide.channel.partner"].sudo()
        for emp in self:
            partner = emp._lms_partner()
            if not partner:
                continue
            channels = Channel.search(
                [("tag_ids", "in", tag.ids)] + emp._visible_courses_domain()
            )
            if not channels:
                continue
            if reset:
                Membership.search(
                    [
                        ("channel_id", "in", channels.ids),
                        ("partner_id", "=", partner.id),
                    ]
                ).unlink()
            channels._action_add_members(partner)

    @api.model
    def _cron_annual_reinduction(self):
        """Yearly: re-assign all Re-Induction courses to every active
        employee, resetting previous completion."""
        employees = self.search([("company_id.parent_id", "!=", False)])
        employees._enroll_tagged_courses("bpro_lms.tag_re_induction", reset=True)
