from odoo import models


class HrDepartureWizard(models.TransientModel):
    _inherit = "hr.departure.wizard"

    def action_register_departure(self):
        res = super().action_register_departure()
        employee = self.employee_id
        # Native action_register_departure never touches res.users - an
        # offboarded employee otherwise keeps a live login indefinitely.
        # Check the outcome (employee.active) rather than replicating the
        # exact archive-vs-metadata-only precondition logic above, so this
        # is correct regardless of which of Odoo's two call paths triggered
        # the wizard.
        if not employee.active and employee.user_id and employee.user_id.active:
            employee.user_id.sudo().active = False
        return res
