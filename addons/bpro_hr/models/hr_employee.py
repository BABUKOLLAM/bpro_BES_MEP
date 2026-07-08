from odoo import api, fields, models

TRACKED_FIELDS = ("job_id", "department_id", "parent_id", "company_id")


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    bpro_employment_history_ids = fields.One2many(
        "bpro.hr.employment.history", "employee_id", string="Employment History", readonly=True
    )

    def _bpro_history_snapshot(self):
        self.ensure_one()
        return {
            "job_id": self.job_id.id,
            "department_id": self.department_id.id,
            "manager_id": self.parent_id.id,
            "company_id": self.company_id.id,
        }

    @api.model_create_multi
    def create(self, vals_list):
        employees = super().create(vals_list)
        today = fields.Date.context_today(self)
        for employee in employees:
            self.env["bpro.hr.employment.history"].sudo().create(
                {
                    "employee_id": employee.id,
                    "date_start": today,
                    **employee._bpro_history_snapshot(),
                }
            )
        return employees

    def write(self, vals):
        # Native mail.thread tracking on job_id/department_id logs chatter
        # messages, but that's unstructured and parent_id (Manager) isn't
        # even tracked - there is no queryable timeline of an employee's
        # internal role/department/manager/company changes anywhere
        # natively. Snapshot the whole state on every write that touches
        # one of these, not one row per field, so a single transfer that
        # changes several fields at once produces one history row.
        watch = self.filtered(lambda e: any(f in vals for f in TRACKED_FIELDS))
        before = {employee.id: employee._bpro_history_snapshot() for employee in watch}
        res = super().write(vals)
        if watch:
            today = fields.Date.context_today(self)
            history_model = self.env["bpro.hr.employment.history"].sudo()
            for employee in watch:
                after = employee._bpro_history_snapshot()
                if after == before[employee.id]:
                    continue
                open_row = history_model.search(
                    [("employee_id", "=", employee.id), ("date_end", "=", False)],
                    limit=1,
                )
                open_row.date_end = today
                history_model.create(
                    {"employee_id": employee.id, "date_start": today, **after}
                )
        return res
