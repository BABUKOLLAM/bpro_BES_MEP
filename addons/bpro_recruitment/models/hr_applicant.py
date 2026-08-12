from odoo import fields, models


class HrApplicant(models.Model):
    _inherit = "hr.applicant"

    evaluation_ids = fields.One2many(
        "bpro.interview.evaluation", "applicant_id", string="Interview Evaluations"
    )

    def _bpro_notify_hod_of_interview(self, evaluation):
        """Native hr_recruitment notifies the assigned interviewer
        (verified in R4.1) but not the requesting department's HOD, who
        may not be an interviewer themselves. This closes that gap -
        "intimated to interview panel/HOD or concerned" from the
        original spec.
        """
        self.ensure_one()
        hod_user = self.department_id.manager_id.user_id
        if not hod_user or not hod_user.partner_id:
            return
        self.message_post(
            body=(
                f"Interview scheduled for {self.partner_name or 'this candidate'} "
                f"({evaluation.interview_type}) with "
                f"{evaluation.interviewer_id.name} on {evaluation.interview_datetime}."
            ),
            partner_ids=[hod_user.partner_id.id],
        )
