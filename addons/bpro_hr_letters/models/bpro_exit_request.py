from odoo import fields, models


class BproExitRequest(models.Model):
    _inherit = "bpro.exit.request"

    relieving_letter_id = fields.Many2one("bpro.hr.letter", readonly=True, copy=False)

    def action_close(self):
        """Every properly offboarded employee should leave with their
        relieving letter ready - created here, at the one place the
        departure becomes final, rather than requested weeks later."""
        res = super().action_close()
        for rec in self:
            if not rec.relieving_letter_id:
                rec.relieving_letter_id = self.env["bpro.hr.letter"].sudo().create({
                    "employee_id": rec.employee_id.id,
                    "letter_type": "experience",
                    "service_to": rec.last_working_day,
                })
        return res
