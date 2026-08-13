from dateutil.relativedelta import relativedelta

from odoo import fields, models


class BproJobOffer(models.Model):
    _inherit = "bpro.job.offer"

    def action_finalize_hiring(self):
        """Every hire made through the recruitment flow enters probation
        automatically - joining date + the company's policy months. The
        one place hiring is finalized is the one place probation should
        start; a separate manual step would just be forgotten."""
        res = super().action_finalize_hiring()
        for rec in self:
            if rec.employee_id and rec.employee_id.probation_state == "confirmed":
                start = rec.joining_date or fields.Date.context_today(rec)
                rec.employee_id.write({
                    "probation_state": "probation",
                    "probation_end_date": start + relativedelta(
                        months=rec.company_id.probation_months or 6
                    ),
                    "confirmation_date": False,
                })
        return res
