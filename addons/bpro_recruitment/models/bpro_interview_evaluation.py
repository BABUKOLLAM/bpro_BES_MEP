from odoo import api, fields, models


class BproInterviewEvaluation(models.Model):
    _name = "bpro.interview.evaluation"
    _description = "Interview Evaluation"
    _order = "interview_datetime desc"

    applicant_id = fields.Many2one(
        "hr.applicant", required=True, ondelete="cascade"
    )
    interviewer_id = fields.Many2one(
        "res.users", required=True, default=lambda self: self.env.user
    )
    interview_type = fields.Selection(
        [("online", "Online"), ("offline", "Offline")],
        default="online",
        required=True,
    )
    interview_datetime = fields.Datetime(
        default=lambda self: fields.Datetime.now()
    )
    marks = fields.Float(help="Out of 100. Optional until the interview happens.")
    remarks = fields.Text()
    recommendation = fields.Selection(
        [
            ("no_comments", "No Comments"),
            ("recommended", "Recommended for Selection"),
            ("on_hold", "On Hold"),
            ("rejected", "Rejected"),
        ],
        default="no_comments",
        required=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            # sudo(): a base interviewer can create their OWN evaluation
            # (granted directly) but native hr_recruitment's interviewer
            # group only grants hr.applicant read access once they're
            # already listed in interviewer_ids - circular for the very
            # first evaluation on an applicant they're new to. Same
            # scoped-sudo() pattern as R4.1's vacancy approval: the real
            # gate is "can this user create an evaluation at all"
            # (enforced by ir.model.access.csv), not a second unrelated
            # native permission for this internal side effect.
            applicant = rec.applicant_id.sudo()
            if rec.interviewer_id not in applicant.interviewer_ids:
                applicant.interviewer_ids = [(4, rec.interviewer_id.id)]
            applicant._bpro_notify_hod_of_interview(rec)
        return records
