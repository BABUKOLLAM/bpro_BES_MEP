import base64

from odoo import fields, models
from odoo.exceptions import UserError


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    # OCA payroll's own credit_note field has no default=False, so new
    # payslips get NULL in Postgres. Payslips.sum() (used by the
    # half-yearly PT accumulation in this module) does
    # "WHEN hp.credit_note = False THEN pl.total ELSE -pl.total" - and
    # NULL = False is NULL in SQL, not TRUE, so it silently falls into the
    # ELSE branch and negates every sum. Re-declaring the field here with
    # an explicit default is the supported way to fix this without
    # touching the vendored module.
    credit_note = fields.Boolean(default=False)

    def action_email_payslip(self):
        """Push distribution (R6.2): email each confirmed slip's PDF to
        the employee. ESS gives pull access ('My Payslips'); factory
        workers respond better to push. Multi-record safe, so it can be
        called from a list selection for the whole payroll run."""
        sent, skipped = 0, []
        for slip in self:
            if slip.state != "done":
                raise UserError(
                    f"{slip.employee_id.name}'s slip is not confirmed - "
                    "only done payslips are distributed."
                )
            email_to = slip.employee_id.work_email or slip.employee_id.private_email
            if not email_to:
                skipped.append(slip.employee_id.name)
                continue
            pdf, _dummy = self.env["ir.actions.report"]._render_qweb_pdf(
                "bpro_payroll.action_report_bpro_payslip", res_ids=slip.ids
            )
            attachment = self.env["ir.attachment"].sudo().create({
                "name": f"Payslip_{slip.employee_id.name}_{slip.date_from.strftime('%Y%m')}.pdf",
                "datas": base64.b64encode(pdf),
                "res_model": "hr.payslip",
                "res_id": slip.id,
            })
            self.env["mail.mail"].sudo().create({
                "subject": f"Payslip — {slip.date_from.strftime('%B %Y')}",
                "email_to": email_to,
                "body_html": (
                    f"<p>Dear {slip.employee_id.name},</p>"
                    f"<p>Please find attached your payslip for "
                    f"{slip.date_from.strftime('%B %Y')}.</p>"
                ),
                "attachment_ids": [(4, attachment.id)],
            }).send()
            sent += 1
        if skipped:
            # Surface the gap rather than silently not delivering -
            # same discipline as the filing wizard.
            raise UserError(
                f"Sent {sent} payslip(s). No email address on file for: "
                + ", ".join(skipped)
            )
        return True
