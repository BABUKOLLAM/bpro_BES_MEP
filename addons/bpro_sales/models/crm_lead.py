from odoo import _, api, models
from odoo.exceptions import ValidationError


class CrmLead(models.Model):
    _inherit = "crm.lead"

    @api.constrains("email_from", "phone", "company_id")
    def _bpro_check_duplicate(self):
        for lead in self:
            base_domain = [
                ("company_id", "=", lead.company_id.id),
                ("id", "!=", lead.id),
            ]
            if lead.email_from:
                dupe = self.search(
                    base_domain + [("email_from", "=", lead.email_from)], limit=1
                )
                if dupe:
                    raise ValidationError(self._bpro_duplicate_message(dupe, "email"))
            if lead.phone:
                dupe = self.search(
                    base_domain + [("phone", "=", lead.phone)], limit=1
                )
                if dupe:
                    raise ValidationError(self._bpro_duplicate_message(dupe, "phone"))

    def _bpro_duplicate_message(self, dupe, matched_on):
        return _(
            "A lead/opportunity with this %(field)s already exists: "
            "#%(id)d - %(name)s, owned by %(owner)s."
        ) % {
            "field": matched_on,
            "id": dupe.id,
            "name": dupe.name,
            "owner": dupe.user_id.name or _("Unassigned"),
        }
