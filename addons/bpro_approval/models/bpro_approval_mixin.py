from odoo import api, fields, models
from odoo.exceptions import AccessError

APPROVAL_ACTIVITY_SUMMARY = "bpro approval required"


class BproApprovalMixin(models.AbstractModel):
    """Inherit this on a concrete model to gate an action behind manager
    approval once a configurable threshold is exceeded. The host model
    must override _approval_policy_key(), _approval_amount() and
    _approval_group_xmlid() — the defaults raise NotImplementedError so a
    missing override fails loudly instead of silently skipping approval.

    Deliberately does NOT _inherit mail.thread/mail.activity.mixin itself
    (needed for action_request_approval's activity_schedule call): some
    host models already have them natively (e.g. sale.order), and this
    mixin independently re-declaring the same bases creates a Python MRO
    conflict when combined with those models. The host model must bring
    mail.thread + mail.activity.mixin itself — either for free (sale.order)
    or by listing them explicitly alongside this mixin (stock.quant does,
    since it has neither natively).
    """

    _name = "bpro.approval.mixin"
    _description = "Threshold-Gated Approval Workflow"

    approval_state = fields.Selection(
        [
            ("none", "No Approval Needed"),
            ("pending", "Pending Approval"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        default="none",
        copy=False,
    )
    approval_requested_by = fields.Many2one(
        "res.users", string="Approval Requested By", copy=False
    )
    approval_decided_by = fields.Many2one(
        "res.users", string="Approval Decided By", copy=False
    )
    approval_decided_at = fields.Datetime(copy=False)
    approval_reason = fields.Char(string="Approval/Rejection Reason", copy=False)

    def _approval_policy_key(self):
        """Return the bpro.policy key used to look up this record's
        threshold. Must be overridden by the host model."""
        raise NotImplementedError(
            "%s must override _approval_policy_key()" % self._name
        )

    def _approval_amount(self):
        """Return the numeric value to compare against the threshold.
        Must be overridden by the host model."""
        raise NotImplementedError("%s must override _approval_amount()" % self._name)

    def _approval_group_xmlid(self):
        """Return the fully-qualified xmlid of the res.groups allowed to
        decide this approval. Must be overridden by the host model."""
        raise NotImplementedError(
            "%s must override _approval_group_xmlid()" % self._name
        )

    def _approval_threshold_exceeded(self):
        self.ensure_one()
        threshold = self.env["bpro.policy"].get_value(
            self.company_id or self.env.company,
            self._approval_policy_key(),
            default=0.0,
        )
        return self._approval_amount() > threshold

    def _approval_group(self):
        return self.env.ref(self._approval_group_xmlid())

    def action_request_approval(self):
        """Call this from a normal save path (write/create), not from
        inside an action you're about to block with `raise UserError(...)`.
        Odoo rolls back the whole transaction when an exception propagates
        out of an action (both in real usage and in the test framework's
        assertRaises, which wraps the block in a savepoint specifically to
        undo it) - a request-approval write made just before such a raise,
        in the same call, is silently discarded along with everything
        else. Host models should request approval proactively, as soon as
        the threshold-crossing value is saved, then have the blocked
        action itself just read approval_state without writing to it.
        """
        for rec in self:
            approver = self.env["res.users"].search(
                [
                    ("groups_id", "in", rec._approval_group().id),
                    ("company_id", "=", (rec.company_id or rec.env.company).id),
                ],
                limit=1,
            )
            rec.write(
                {
                    "approval_state": "pending",
                    "approval_requested_by": self.env.user.id,
                    "approval_decided_by": False,
                    "approval_decided_at": False,
                    "approval_reason": False,
                }
            )
            rec.activity_schedule(
                "mail.mail_activity_data_todo",
                summary=APPROVAL_ACTIVITY_SUMMARY,
                note="%s exceeds the configured threshold and needs approval."
                % rec.display_name,
                user_id=approver.id if approver else self.env.user.id,
            )
        return True

    def _approval_check_is_approver(self):
        self.ensure_one()
        if self._approval_group() not in self.env.user.groups_id:
            raise AccessError("Only an approver may decide on this request.")

    @api.model_create_multi
    def create(self, vals_list):
        """action_approve()/action_reject() are the only sanctioned way to
        set approval_state to a decided value - block it at create() too,
        not just write() below, so a record can't be born pre-approved by
        anyone with plain create access to the host model."""
        for vals in vals_list:
            if vals.get("approval_state") in ("approved", "rejected"):
                if self._approval_group() not in self.env.user.groups_id:
                    raise AccessError(
                        "Only an approver may create a record already in a "
                        "decided approval state."
                    )
        return super().create(vals_list)

    def write(self, vals):
        """Deciding an approval must always go through action_approve()/
        action_reject() (which call _approval_check_is_approver() before
        writing) - without this override, any user with ordinary write
        access to the host model (e.g. a salesperson on sale.order, a
        stock user on stock.quant) could set approval_state='approved'
        directly via ORM/RPC/an automation rule and skip the approver
        check those actions exist to enforce."""
        if vals.get("approval_state") in ("approved", "rejected"):
            for rec in self:
                rec._approval_check_is_approver()
        return super().write(vals)

    def _approval_close_activity(self, feedback):
        self.activity_ids.filtered(
            lambda a: a.summary == APPROVAL_ACTIVITY_SUMMARY
        ).action_feedback(feedback=feedback)

    def action_approve(self):
        for rec in self:
            rec._approval_check_is_approver()
            rec.write(
                {
                    "approval_state": "approved",
                    "approval_decided_by": self.env.user.id,
                    "approval_decided_at": fields.Datetime.now(),
                }
            )
            rec._approval_close_activity("Approved")
        return True

    def action_reject(self, reason=None):
        for rec in self:
            rec._approval_check_is_approver()
            rec.write(
                {
                    "approval_state": "rejected",
                    "approval_decided_by": self.env.user.id,
                    "approval_decided_at": fields.Datetime.now(),
                    "approval_reason": reason,
                }
            )
            rec._approval_close_activity(reason or "Rejected")
        return True
