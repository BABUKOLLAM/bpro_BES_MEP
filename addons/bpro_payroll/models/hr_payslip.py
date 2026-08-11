from odoo import fields, models


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
