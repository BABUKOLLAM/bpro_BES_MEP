import base64

from odoo import api, fields, models
from odoo.exceptions import UserError

# Selection key -> (target model, human label). Kept here rather than as
# raw model names in the selection so customers/vendors (both
# res.partner) stay distinct choices for the uploader.
TARGETS = {
    "crm_lead": ("crm.lead", "CRM Leads"),
    "customer": ("res.partner", "Customers"),
    "vendor": ("res.partner", "Vendors"),
    "product": ("product.template", "Products"),
    "employee": ("hr.employee", "Employees"),
    "opening_stock": ("stock.quant", "Opening Stock"),
    "bom": ("mrp.bom", "Bills of Materials"),
}


class BproDataUpload(models.Model):
    _name = "bpro.data.upload"
    _description = "Data Upload (manager-approved bulk import)"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(required=True, default="Data Upload", tracking=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    target_type = fields.Selection(
        [(key, label) for key, (_m, label) in TARGETS.items()],
        required=True,
        tracking=True,
        help="Which template this file was filled from - use the matching "
        "template from /downloads/templates/.",
    )
    file = fields.Binary(string="Filled Template (.xlsx)", required=True, attachment=True)
    file_name = fields.Char()
    uploaded_by = fields.Many2one(
        "res.users", default=lambda self: self.env.user, readonly=True
    )
    manager_user_id = fields.Many2one(
        "res.users",
        string="Approving Manager",
        compute="_compute_manager_user_id",
        store=True,
        readonly=False,
        tracking=True,
        help="Defaults to the uploader's own manager (or department head). "
        "Any Direct Import user (admin) can also approve.",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Waiting Approval"),
            ("approved", "Approved & Imported"),
            ("rejected", "Rejected"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    rejection_reason = fields.Text(readonly=True, copy=False)
    imported_count = fields.Integer(readonly=True, copy=False)
    result_log = fields.Text(readonly=True, copy=False)

    @api.depends("uploaded_by")
    def _compute_manager_user_id(self):
        for rec in self:
            employee = rec.uploaded_by.employee_id
            rec.manager_user_id = (
                employee.parent_id.user_id
                or employee.department_id.manager_id.user_id
                or rec.manager_user_id
            )

    # ------------------------------------------------------------- helpers
    def _is_approver(self):
        self.ensure_one()
        return (
            self.env.user == self.manager_user_id
            or self.env.user.has_group("bpro_data_tools.group_direct_import")
        )

    # ------------------------------------------------------------- actions
    def action_submit(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError("Only draft uploads can be submitted.")
            if not rec.manager_user_id:
                raise UserError(
                    "No approving manager could be determined - set one, or "
                    "ask HR to set your manager on your employee record."
                )
            rec.state = "submitted"
            rec.activity_schedule(
                "mail.mail_activity_data_todo",
                user_id=rec.manager_user_id.id,
                summary=f"Review data upload: {rec.file_name or rec.name}",
                note="Open the record, download the file, check correctness, "
                "then Approve (imports the data) or Reject with a reason.",
            )
            rec.message_post(
                body=f"Submitted for approval to {rec.manager_user_id.name}.",
                partner_ids=rec.manager_user_id.partner_id.ids,
            )

    def action_approve(self):
        for rec in self:
            if rec.state != "submitted":
                raise UserError("Only submitted uploads can be approved.")
            if not rec._is_approver():
                raise UserError(
                    "Only the assigned manager (or a Direct Import user) may "
                    "approve this upload."
                )
            result = rec._run_import()
            rec.write({
                "state": "approved",
                "imported_count": len(result.get("ids") or []),
                "result_log": "\n".join(
                    m.get("message", str(m)) for m in result.get("messages") or []
                ) or "Imported cleanly.",
            })
            rec.activity_feedback(["mail.mail_activity_data_todo"])
            rec.message_post(
                body=f"Approved by {self.env.user.name} - "
                f"{rec.imported_count} records imported.",
                partner_ids=rec.uploaded_by.partner_id.ids,
            )

    def action_reject(self):
        for rec in self:
            if rec.state != "submitted":
                raise UserError("Only submitted uploads can be rejected.")
            if not rec._is_approver():
                raise UserError("Only the assigned manager may reject this upload.")
            if not rec.rejection_reason:
                raise UserError(
                    "Write the reason into 'Rejection Reason' first - the "
                    "uploader needs to know what to fix."
                )
        self.write({"state": "rejected"})
        for rec in self:
            rec.activity_feedback(["mail.mail_activity_data_todo"])
            rec.message_post(
                body=f"Rejected by {self.env.user.name}: {rec.rejection_reason}",
                partner_ids=rec.uploaded_by.partner_id.ids,
            )

    def action_reset_draft(self):
        for rec in self:
            if rec.state != "rejected":
                raise UserError("Only rejected uploads can be reset to draft.")
        self.write({"state": "draft", "rejection_reason": False})

    def write(self, vals):
        # An approver may edit rejection_reason on a submitted record; the
        # uploader may not silently swap the file after submitting.
        if "file" in vals:
            for rec in self:
                if rec.state not in ("draft", "rejected"):
                    raise UserError(
                        "The file cannot be changed after submission - reject "
                        "and resubmit instead."
                    )
        return super().write(vals)

    # ------------------------------------------------------------- import
    def _run_import(self):
        self.ensure_one()
        model, _label = TARGETS[self.target_type]
        importer = self.env["base_import.import"].sudo().create({
            "res_model": model,
            "file": base64.b64decode(self.file),
            "file_name": self.file_name or "upload.xlsx",
            "file_type": "application/vnd.openxmlformats-officedocument"
            ".spreadsheetml.sheet",
        })
        preview = importer.parse_preview({"has_headers": True})
        if preview.get("error"):
            raise UserError(f"The file could not be read: {preview['error']}")
        headers = preview["headers"]
        # Template headers ARE technical field paths - map 1:1.
        result = importer.with_context(bpro_upload_approved=True).execute_import(
            headers, headers, {"has_headers": True}
        )
        errors = [
            m for m in result.get("messages") or []
            if m.get("type") in ("error", "critical")
        ]
        if errors and not result.get("ids"):
            raise UserError(
                "Import failed - nothing was created:\n"
                + "\n".join(e.get("message", str(e)) for e in errors[:10])
            )
        return result
