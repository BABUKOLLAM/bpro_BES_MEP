from odoo import fields, models


class SlideChannel(models.Model):
    """Content ownership per the roadmap: a course owned by bpro Corporate
    (the parent company) is global and visible to every client company;
    a course owned by a client company stays private to that client."""

    _inherit = "slide.channel"

    company_id = fields.Many2one(
        "res.company",
        string="Owner Company",
        default=lambda self: self.env.company,
        help="Global courses (Induction, Compliance, Policy) belong to "
        "bpro Corporate and are visible to all client companies. "
        "Client-specific courses stay private to that client.",
    )

    def write(self, vals):
        was_published = {c.id: c.is_published for c in self}
        res = super().write(vals)
        if vals.get("is_published") or vals.get("website_published"):
            newly_published = self.filtered(
                lambda c: c.is_published and not was_published.get(c.id)
            )
            newly_published._push_policy_updates()
        return res

    def _push_policy_updates(self):
        """Roadmap P3: a newly published Policy Updation course is pushed
        to every employee it is visible to (own company subtree, or all
        client companies when owned by bpro Corporate / no company)."""
        tag = self.env.ref("bpro_lms.tag_policy_updation", raise_if_not_found=False)
        if not tag:
            return
        Employee = self.env["hr.employee"].sudo()
        for channel in self.filtered(lambda c: tag in c.tag_ids):
            domain = []
            if channel.company_id:
                domain = [("company_id", "child_of", channel.company_id.id)]
            partners = Employee.search(domain)._lms_partners()
            if partners:
                channel.sudo()._action_add_members(partners)
