from odoo import fields, models


class HrEmploymentHistory(models.Model):
    _name = "bpro.hr.employment.history"
    _description = "Employee Job/Department/Manager/Company History"
    _order = "date_start desc"

    employee_id = fields.Many2one(
        "hr.employee", required=True, ondelete="cascade", index=True
    )
    company_id = fields.Many2one("res.company")
    job_id = fields.Many2one("hr.job")
    department_id = fields.Many2one("hr.department")
    manager_id = fields.Many2one("hr.employee")
    date_start = fields.Date(required=True)
    date_end = fields.Date(help="Empty means this is the current, still-open period.")

    _sql_constraints = [
        (
            "date_check",
            "CHECK ((date_start <= date_end OR date_end IS NULL))",
            "The start date must be anterior to the end date.",
        ),
    ]
