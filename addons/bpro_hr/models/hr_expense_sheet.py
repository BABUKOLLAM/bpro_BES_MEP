from odoo import _, fields, models
from odoo.exceptions import UserError

FINANCE_APPROVAL_ACTIVITY_SUMMARY = "bpro Finance approval required"


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    # Not built on bpro.approval.mixin: hr.expense.sheet already has its own
    # native approval_state field (submit/approve/cancel, feeding
    # _compute_state) - reinheriting the mixin's approval_state field of the
    # same name would silently redefine its selection values and break
    # native state computation. This bespoke field mirrors the mixin's
    # threshold-gate shape by hand instead.
    bpro_finance_approval_state = fields.Selection(
        [
            ("none", "No Approval Needed"),
            ("pending", "Pending Finance Approval"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        default="none",
        copy=False,
    )

    def _bpro_finance_approval_threshold_exceeded(self):
        self.ensure_one()
        threshold = self.env["bpro.policy"].get_value(
            self.company_id, "hr_expense_finance_approval_pct", default=0.0
        )
        return self.total_amount > threshold

    def _do_submit(self):
        super()._do_submit()
        for sheet in self:
            if sheet._bpro_finance_approval_threshold_exceeded():
                sheet.bpro_finance_approval_state = "pending"
                sheet.activity_schedule(
                    "mail.mail_activity_data_todo",
                    summary=FINANCE_APPROVAL_ACTIVITY_SUMMARY,
                    note=_(
                        "%s exceeds the company's expense approval threshold "
                        "and needs Finance Manager approval before the "
                        "direct manager can approve it."
                    )
                    % sheet.display_name,
                    user_id=self.env.user.id,
                )
            else:
                sheet.bpro_finance_approval_state = "none"

    def action_approve_expense_sheets(self):
        # Read-only check, same reasoning as sale.order's
        # action_quotation_send: the Finance approval request itself is
        # raised proactively at submission time (_do_submit above), not
        # here - raising UserError rolls back the whole transaction.
        for sheet in self:
            if sheet.bpro_finance_approval_state in ("pending", "rejected"):
                raise UserError(
                    _(
                        "%s exceeds the expense approval threshold and is "
                        "pending Finance Manager approval. It can be "
                        "approved once Finance signs off."
                    )
                    % sheet.display_name
                )
        return super().action_approve_expense_sheets()

    def _bpro_check_is_finance_approver(self):
        if self.env.ref("account.group_account_manager") not in self.env.user.groups_id:
            raise UserError(_("Only a Finance Manager may decide this approval."))

    def action_bpro_finance_approve(self):
        for sheet in self:
            sheet._bpro_check_is_finance_approver()
            sheet.bpro_finance_approval_state = "approved"
            sheet.activity_ids.filtered(
                lambda a: a.summary == FINANCE_APPROVAL_ACTIVITY_SUMMARY
            ).action_feedback(feedback="Approved by Finance")

    def action_bpro_finance_reject(self):
        for sheet in self:
            sheet._bpro_check_is_finance_approver()
            sheet.bpro_finance_approval_state = "rejected"
            sheet.activity_ids.filtered(
                lambda a: a.summary == FINANCE_APPROVAL_ACTIVITY_SUMMARY
            ).action_feedback(feedback="Rejected by Finance")
