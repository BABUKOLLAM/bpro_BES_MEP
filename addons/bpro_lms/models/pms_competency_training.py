from odoo import fields, models


class PmsCompetency(models.Model):
    _inherit = "bpro.pms.competency"

    course_ids = fields.Many2many(
        "slide.channel",
        string="Courses",
        help="Completing an appraisal auto-enrolls employees with this "
        "competency gap into these courses.",
    )


class PmsTrainingNeed(models.Model):
    _inherit = "bpro.pms.training.need"

    def _auto_enroll(self):
        """The roadmap P6 integration: appraisal outcome -> training need
        -> auto-enrollment in the matching LMS courses (only those the
        employee's company is allowed to see)."""
        for need in self.filtered(lambda n: n.state == "identified"):
            partner = need.employee_id._lms_partner()
            if not partner:
                continue
            # visible = no owner, or owner is the employee's company or an
            # ancestor of it (e.g. bpro Corporate)
            ancestors = (need.employee_id.company_id.parent_path or "").split("/")
            channels = need.competency_id.course_ids.filtered(
                lambda c: not c.company_id or str(c.company_id.id) in ancestors
            )
            if channels:
                channels.sudo()._action_add_members(partner)
        return super()._auto_enroll()


class HrEmployeeLms(models.Model):
    _inherit = "hr.employee"

    lms_completion = fields.Integer(
        string="Avg Training Completion (%)", compute="_compute_lms_completion"
    )

    def _compute_lms_completion(self):
        Membership = self.env["slide.channel.partner"].sudo()
        for emp in self:
            partner = emp._lms_partner()
            memberships = (
                Membership.search([("partner_id", "=", partner.id)])
                if partner
                else Membership
            )
            emp.lms_completion = (
                int(sum(memberships.mapped("completion")) / len(memberships))
                if memberships
                else 0
            )
