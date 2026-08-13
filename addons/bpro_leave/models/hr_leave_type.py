from odoo import fields, models


class HrLeaveType(models.Model):
    _inherit = "hr.leave.type"

    bpro_is_lop_type = fields.Boolean(
        string="Loss of Pay",
        help="Marks this leave type as unpaid for payroll purposes. Native "
        "hr.leave.type has no paid/unpaid concept of its own - an approved "
        "leave under a type flagged here counts toward the LOP proration "
        "rule (bpro_payroll's LOP_FACTOR helper) exactly like a confirmed "
        "bpro.attendance.exception day. Leave types not flagged here are "
        "paid in full regardless of allocation balance.",
    )
