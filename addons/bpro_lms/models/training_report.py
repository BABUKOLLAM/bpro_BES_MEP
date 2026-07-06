from odoo import fields, models, tools


class BproTrainingReport(models.Model):
    """Training compliance: one row per employee x course enrollment.
    The three-tier record rules scope the same report for every role:
    HR sees the company, HOD their department, employees themselves,
    bpro Super Admin all clients."""

    _name = "bpro.training.report"
    _description = "Training Compliance"
    _auto = False
    _rec_name = "employee_id"
    _order = "company_id, department_id, employee_id"

    employee_id = fields.Many2one("hr.employee", string="Employee", readonly=True)
    department_id = fields.Many2one("hr.department", string="Department", readonly=True)
    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    channel_id = fields.Many2one("slide.channel", string="Course", readonly=True)
    completion = fields.Float(string="Completion %", readonly=True, aggregator="avg")
    is_completed = fields.Boolean(string="Completed", readonly=True)
    member_status = fields.Char(string="Status", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
            CREATE OR REPLACE VIEW bpro_training_report AS (
                SELECT scp.id AS id,
                       e.id AS employee_id,
                       e.department_id AS department_id,
                       e.company_id AS company_id,
                       scp.channel_id AS channel_id,
                       scp.completion AS completion,
                       (scp.member_status = 'completed') AS is_completed,
                       scp.member_status AS member_status
                FROM slide_channel_partner scp
                JOIN hr_employee e
                  ON e.active
                 AND (e.work_contact_id = scp.partner_id
                      OR e.user_id IN (SELECT u.id FROM res_users u
                                       WHERE u.partner_id = scp.partner_id))
            )
            """
        )
