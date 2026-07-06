from odoo import fields, models


class PmsTrainingNeed(models.Model):
    """A competency gap identified for an employee, usually during an
    appraisal. When the appraisal completes, the need is processed:
    bpro LMS auto-enrolls the employee in the competency's courses."""

    _name = "bpro.pms.training.need"
    _description = "Training Need"
    _inherit = ["mail.thread"]
    _order = "id desc"

    employee_id = fields.Many2one("hr.employee", string="Employee", required=True)
    competency_id = fields.Many2one(
        "bpro.pms.competency", string="Competency", required=True
    )
    appraisal_id = fields.Many2one("bpro.pms.appraisal", string="Source Appraisal")
    note = fields.Char(string="Note")
    state = fields.Selection(
        [
            ("identified", "Identified"),
            ("enrolled", "Enrolled"),
            ("completed", "Completed"),
        ],
        default="identified",
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company", related="employee_id.company_id", store=True, readonly=True
    )

    def _auto_enroll(self):
        """Base behavior: mark as enrolled. bpro LMS extends this to
        actually enroll the employee in the competency's courses."""
        return self.filtered(lambda n: n.state == "identified").write(
            {"state": "enrolled"}
        )

    def action_mark_completed(self):
        return self.write({"state": "completed"})
