from odoo import _, api, fields, models
from odoo.addons.project.models.project_task import CLOSED_STATES
from odoo.exceptions import UserError


class ProjectTask(models.Model):
    _name = "project.task"
    _inherit = ["project.task", "bpro.approval.mixin"]

    bpro_workload_warning = fields.Char(compute="_compute_bpro_workload_warning")

    def _approval_policy_key(self):
        return "project_budget_overrun_pct"

    def _approval_amount(self):
        self.ensure_one()
        if not self.allocated_hours:
            return 0.0
        return (self.effective_hours - self.allocated_hours) / self.allocated_hours * 100.0

    def _approval_group_xmlid(self):
        return "project.group_project_manager"

    def _bpro_sync_budget_approval(self):
        """Called from account_analytic_line.py whenever a timesheet entry
        linked to a task is created/changed/removed. Re-evaluates the
        approval gate as part of that normal save - a previously-decided
        task is reset, and any task now over threshold gets a fresh
        approval request - so write() only ever needs to read
        approval_state, never write to it."""
        self.filtered(
            lambda t: t.approval_state in ("approved", "rejected")
        ).write({"approval_state": "none"})
        self.filtered(
            lambda t: t.approval_state == "pending" and not t._approval_threshold_exceeded()
        ).write({"approval_state": "none"})
        self.filtered(
            lambda t: t.approval_state == "none" and t._approval_threshold_exceeded()
        ).action_request_approval()

    @api.depends("user_ids", "allocated_hours", "is_closed")
    def _compute_bpro_workload_warning(self):
        for task in self:
            if not task.user_ids or task.is_closed:
                task.bpro_workload_warning = False
                continue
            threshold = self.env["bpro.policy"].get_value(
                task.company_id or self.env.company,
                "project_employee_capacity_hours",
                default=0.0,
            )
            overloaded = []
            for user in task.user_ids:
                open_tasks = self.search(
                    [("user_ids", "in", user.id), ("is_closed", "=", False)]
                )
                total = sum(open_tasks.mapped("allocated_hours"))
                if total > threshold:
                    overloaded.append(
                        _("%(user)s (%(hours).1fh open across %(count)d tasks)")
                        % {
                            "user": user.name,
                            "hours": total,
                            "count": len(open_tasks),
                        }
                    )
            task.bpro_workload_warning = "; ".join(overloaded) if overloaded else False

    def write(self, vals):
        # Read-only check, same reasoning as sale.order's
        # action_quotation_send: the approval request itself is raised
        # proactively when the timesheet entry is saved
        # (account_analytic_line.py), not here - raising UserError rolls
        # back the whole transaction.
        if vals.get("state") in CLOSED_STATES:
            blocked = self.filtered(
                lambda t: t._approval_threshold_exceeded()
                and t.approval_state != "approved"
            )
            if blocked:
                raise UserError(
                    _(
                        "%s has logged hours exceeding its allocated budget "
                        "threshold and is pending Project Manager approval. "
                        "It can be closed once approved."
                    )
                    % ", ".join(blocked.mapped("name"))
                )
        # bpro_workload_warning aggregates sibling tasks via a plain
        # search() inside the compute, which Odoo's dependency tracker
        # can't see - a write here would otherwise leave every sibling
        # task's cached value stale until something else happens to
        # invalidate it.
        needs_invalidation = bool(vals.keys() & {"state", "allocated_hours", "user_ids"})
        affected_users = self.user_ids if needs_invalidation else self.env["res.users"]
        res = super().write(vals)
        if needs_invalidation:
            affected_users |= self.user_ids
            if affected_users:
                self.search(
                    [("user_ids", "in", affected_users.ids)]
                ).invalidate_recordset(["bpro_workload_warning"])
        return res
