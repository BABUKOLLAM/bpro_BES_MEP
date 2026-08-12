from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    employee_code = fields.Char(
        readonly=True,
        copy=False,
        help="Auto-generated on hiring finalization (bpro.job.offer's "
        "Finalize Hiring action) via the bpro.employee.code sequence - "
        "not editable here, and never reused even if an employee record "
        "is later archived.",
    )

    _sql_constraints = [
        (
            "employee_code_unique",
            "unique(employee_code)",
            "Employee code must be unique.",
        ),
    ]
