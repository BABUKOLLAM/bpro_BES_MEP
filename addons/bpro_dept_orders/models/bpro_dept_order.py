from odoo import api, fields, models
from odoo.exceptions import UserError


class BproDeptOrder(models.Model):
    _name = "bpro.dept.order"
    _description = "Department Order / Indent"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(
        default="New", readonly=True, copy=False, tracking=True
    )
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    department_id = fields.Many2one(
        "hr.department",
        required=True,
        tracking=True,
        default=lambda self: self.env.user.employee_id.department_id,
        help="The ordering department. Its head is the approver.",
    )
    requested_by = fields.Many2one(
        "res.users", default=lambda self: self.env.user, readonly=True
    )
    approver_user_id = fields.Many2one(
        "res.users",
        string="Approver (HOD)",
        compute="_compute_approver_user_id",
        store=True,
        help="Head of the ordering department.",
    )
    order_type = fields.Selection(
        [("material", "Material Issue (from Stores)"),
         ("purchase", "Purchase Request")],
        required=True,
        default="material",
        tracking=True,
    )
    vendor_id = fields.Many2one(
        "res.partner",
        string="Suggested Vendor",
        domain="[('supplier_rank', '>', 0)]",
        help="Purchase requests only. May be left empty - the Purchase "
        "team fills it before creating the RFQ.",
    )
    reason = fields.Text(
        string="Purpose / Justification",
        help="What the material is needed for - the HOD sees this.",
    )
    line_ids = fields.One2many("bpro.dept.order.line", "order_id", copy=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Waiting HOD Approval"),
            ("approved", "Approved"),
            ("processed", "Processed"),
            ("rejected", "Rejected"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    rejection_reason = fields.Text(readonly=True, copy=False)
    picking_id = fields.Many2one(
        "stock.picking", readonly=True, copy=False,
        groups="stock.group_stock_user",
    )
    purchase_order_id = fields.Many2one(
        "purchase.order", readonly=True, copy=False,
        groups="purchase.group_purchase_user",
    )
    # Plain requesters/HODs have no read rights on pickings/POs; these
    # sudo-computed references let them still see what their order became.
    picking_ref = fields.Char(compute="_compute_doc_refs", string="Issue Document")
    purchase_order_ref = fields.Char(compute="_compute_doc_refs", string="RFQ / PO")

    def _compute_doc_refs(self):
        for rec in self:
            sudo_rec = rec.sudo()
            rec.picking_ref = sudo_rec.picking_id.name or False
            rec.purchase_order_ref = sudo_rec.purchase_order_id.name or False

    @api.depends("department_id")
    def _compute_approver_user_id(self):
        for rec in self:
            rec.approver_user_id = rec.department_id.manager_id.user_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "bpro.dept.order"
                ) or "New"
        return super().create(vals_list)

    def _check_approver(self):
        self.ensure_one()
        if self.env.user == self.requested_by and not self.env.user.has_group(
            "base.group_system"
        ):
            raise UserError("You cannot approve your own order.")
        if (
            self.env.user != self.approver_user_id
            and not self.env.user.has_group("base.group_system")
        ):
            raise UserError(
                f"Only {self.approver_user_id.name or 'the department head'} "
                "(HOD of the ordering department) can approve or reject this."
            )

    # ------------------------------------------------------------- actions
    def action_submit(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError("Only draft orders can be submitted.")
            if not rec.line_ids:
                raise UserError("Add at least one product line first.")
            if not rec.approver_user_id:
                raise UserError(
                    f"Department '{rec.department_id.name}' has no head with "
                    "a login - ask HR to set the department manager."
                )
            rec.state = "submitted"
            rec.activity_schedule(
                "mail.mail_activity_data_todo",
                user_id=rec.approver_user_id.id,
                summary=f"Approve department order {rec.name}",
                note=f"{rec.requested_by.name} ({rec.department_id.name}) "
                f"requests {len(rec.line_ids)} item(s). "
                f"Reason: {rec.reason or 'not stated'}",
            )
            rec.message_post(
                body=f"Submitted for approval to {rec.approver_user_id.name}.",
                partner_ids=rec.approver_user_id.partner_id.ids,
            )

    def action_approve(self):
        for rec in self:
            if rec.state != "submitted":
                raise UserError("Only submitted orders can be approved.")
            rec._check_approver()
            if rec.order_type == "material":
                rec._create_issue_picking()
                rec.state = "processed"
                body = (
                    f"Approved - internal issue {rec.sudo().picking_id.name} "
                    "created for Stores to validate."
                )
            else:
                rec.state = "approved"
                body = (
                    "Approved - waiting for the Purchase team to assign a "
                    "vendor and create the RFQ."
                )
            rec.activity_feedback(["mail.mail_activity_data_todo"])
            rec.message_post(body=body, partner_ids=rec.requested_by.partner_id.ids)

    def action_reject(self):
        for rec in self:
            if rec.state != "submitted":
                raise UserError("Only submitted orders can be rejected.")
            rec._check_approver()
            if not rec.rejection_reason:
                raise UserError("Write the rejection reason first.")
        self.write({"state": "rejected"})
        for rec in self:
            rec.activity_feedback(["mail.mail_activity_data_todo"])
            rec.message_post(
                body=f"Rejected: {rec.rejection_reason}",
                partner_ids=rec.requested_by.partner_id.ids,
            )

    def action_reset_draft(self):
        for rec in self:
            if rec.state != "rejected":
                raise UserError("Only rejected orders can be reset to draft.")
        self.write({"state": "draft", "rejection_reason": False})

    def action_create_rfq(self):
        for rec in self:
            if rec.state != "approved" or rec.order_type != "purchase":
                raise UserError("Only approved purchase requests get an RFQ.")
            if not rec.vendor_id:
                raise UserError("Set the vendor first (Purchase team).")
            if not (
                self.env.su
                or self.env.user.has_group("purchase.group_purchase_user")
                or self.env.user.has_group("base.group_system")
            ):
                raise UserError("Only the Purchase team creates the RFQ.")
            # sudo(): the button is gated to purchase users above - that is
            # the real permission boundary (same scoped-sudo pattern as
            # bpro_recruitment's vacancy approval).
            po = self.env["purchase.order"].sudo().create({
                "partner_id": rec.vendor_id.id,
                "origin": rec.name,
                "department_id": rec.department_id.id,
                "order_line": [
                    (0, 0, {
                        "product_id": line.product_id.id,
                        "name": line.description or line.product_id.display_name,
                        "product_qty": line.quantity,
                        "product_uom": (line.uom_id or line.product_id.uom_id).id,
                        "price_unit": line.price_estimate
                        or line.product_id.standard_price,
                    })
                    for line in rec.line_ids
                ],
            })
            rec.sudo().write({"purchase_order_id": po.id, "state": "processed"})
            rec.message_post(body=f"RFQ {po.name} created.")  # po is sudo already

    # ------------------------------------------------------------- helpers
    def _get_dept_consumption_location(self):
        """One virtual consumption location per department - validating the
        issue picking moves stock out of inventory (consumed by the
        department) while keeping full traceability by location."""
        self.ensure_one()
        Location = self.env["stock.location"].sudo()
        parent = Location.search(
            [("name", "=", "Department Consumption"),
             ("usage", "=", "view"),
             ("company_id", "=", self.company_id.id)], limit=1,
        ) or Location.create({
            "name": "Department Consumption", "usage": "view",
            "company_id": self.company_id.id,
        })
        loc = Location.search(
            [("name", "=", self.department_id.name),
             ("location_id", "=", parent.id)], limit=1,
        ) or Location.create({
            "name": self.department_id.name, "usage": "customer",
            "location_id": parent.id, "company_id": self.company_id.id,
        })
        return loc

    def _create_issue_picking(self):
        self.ensure_one()
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.company_id.id)], limit=1
        )
        picking_type = warehouse.out_type_id
        dest = self._get_dept_consumption_location()
        # sudo(): the HOD approving the indent is the permission gate;
        # requiring every HOD to also hold Inventory rights just to spawn
        # the issue document would be a second unrelated gate (same
        # scoped-sudo pattern as bpro_recruitment's approvals).
        picking = self.env["stock.picking"].sudo().create({
            "picking_type_id": picking_type.id,
            "location_id": warehouse.lot_stock_id.id,
            "location_dest_id": dest.id,
            "origin": self.name,
            "department_id": self.department_id.id,
            "move_ids": [
                (0, 0, {
                    "name": line.description or line.product_id.display_name,
                    "product_id": line.product_id.id,
                    "product_uom_qty": line.quantity,
                    "product_uom": (line.uom_id or line.product_id.uom_id).id,
                    "location_id": warehouse.lot_stock_id.id,
                    "location_dest_id": dest.id,
                })
                for line in self.line_ids
                if line.product_id.is_storable
            ],
        })
        if not picking.move_ids:
            picking.unlink()
            raise UserError(
                "None of the lines are storable products - nothing for "
                "Stores to issue."
            )
        picking.sudo().action_confirm()
        picking.sudo().action_assign()
        self.sudo().picking_id = picking


class BproDeptOrderLine(models.Model):
    _name = "bpro.dept.order.line"
    _description = "Department Order Line"

    order_id = fields.Many2one(
        "bpro.dept.order", required=True, ondelete="cascade"
    )
    product_id = fields.Many2one("product.product", required=True)
    description = fields.Char()
    quantity = fields.Float(default=1.0, required=True)
    uom_id = fields.Many2one(
        "uom.uom",
        compute="_compute_uom_id",
        store=True,
        readonly=False,
        help="Defaults to the product's own unit.",
    )
    price_estimate = fields.Float(
        help="Purchase requests only - rough unit price if known."
    )

    @api.depends("product_id")
    def _compute_uom_id(self):
        for line in self:
            if line.product_id:
                line.uom_id = line.product_id.uom_id
