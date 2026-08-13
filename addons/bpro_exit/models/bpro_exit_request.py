from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError

STANDARD_CLEARANCE_LINES = [
    ("asset", "Asset Return"),
    ("hod", "Department / HOD Sign-off"),
    ("finance", "Finance Sign-off"),
    ("it", "IT / Access Sign-off"),
]


class BproExitRequest(models.Model):
    _name = "bpro.exit.request"
    _description = "Exit / Separation Request"
    _order = "create_date desc"
    _rec_name = "employee_id"

    employee_id = fields.Many2one(
        "hr.employee", required=True, ondelete="restrict",
        default=lambda self: self.env.user.employee_id,
        help="Defaults to the logged-in user's own employee record - "
        "the self-service resignation case. HR picks a different "
        "employee when filing on someone's behalf.",
    )
    department_id = fields.Many2one(related="employee_id.department_id", store=True)
    company_id = fields.Many2one(related="employee_id.company_id", store=True)
    resignation_date = fields.Date(
        default=lambda self: fields.Date.context_today(self), required=True
    )
    reason = fields.Text(string="Reason for Leaving")
    notice_days = fields.Integer(
        default=lambda self: self.env.company.exit_notice_days,
        help="Prefilled from company policy - HR can shorten or waive "
        "per case (2026-08-13 scoping decision).",
    )
    accepted_date = fields.Date(readonly=True, copy=False)
    last_working_day = fields.Date(
        help="Computed as acceptance date + notice days on acceptance, "
        "but editable - the notice can be waived or extended by HR.",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("accepted", "Clearance In Progress"),
            ("settled", "Settled"),
            ("closed", "Closed"),
        ],
        default="draft",
        required=True,
        copy=False,
    )
    clearance_line_ids = fields.One2many(
        "bpro.exit.clearance.line", "exit_id", copy=False
    )
    clearance_done = fields.Boolean(compute="_compute_clearance_done")

    # Exit interview - lightweight, on the same record.
    exit_interview_date = fields.Date()
    exit_interview_by = fields.Many2one("res.users")
    exit_interview_notes = fields.Text()

    # Full & Final settlement. Computed by the button, then editable -
    # the statutory math is a correct default, not a straitjacket
    # (edge cases like death/disability gratuity below 5 years are
    # HR-judgment territory, not code).
    service_start_date = fields.Date(
        help="Prefilled from the employee's earliest contract start - "
        "the gratuity 'continuous service' clock. Editable if the real "
        "service start differs (e.g. prior stint counted by agreement).",
    )
    monthly_basic = fields.Float(
        readonly=True, copy=False,
        help="Last drawn monthly Basic from the current contract "
        "(ctc_annual/12 x basic_percent) - the gratuity and EL "
        "encashment wage base.",
    )
    gratuity_years = fields.Integer(readonly=True, copy=False)
    gratuity_amount = fields.Float(
        copy=False,
        help="15/26 x monthly Basic x completed years (>6-month "
        "fraction rounds up), zero below 5 years' service, capped at "
        "the company's configured statutory ceiling. Editable for "
        "cases the Act treats specially (death/disability waives the "
        "5-year rule).",
    )
    el_balance_days = fields.Float(readonly=True, copy=False)
    el_encashment_amount = fields.Float(
        copy=False,
        help="Factories Act s79(11): unavailed Earned Leave paid out "
        "on separation - EL balance x Basic/26 (26-day divisor per "
        "standard factory wage practice).",
    )
    notice_shortfall_days = fields.Integer(readonly=True, copy=False)
    notice_recovery_amount = fields.Float(
        copy=False,
        help="Prefilled as shortfall days x (monthly gross/30) when "
        "the served notice is shorter than agreed - editable, HR may "
        "waive recovery.",
    )
    other_addition = fields.Float(help="Any other payable (bonus, reimbursements...).")
    other_deduction = fields.Float(help="Any other recovery (advances, damages...).")
    settlement_total = fields.Float(readonly=True, copy=False)
    settlement_computed = fields.Boolean(readonly=True, copy=False)

    @api.depends("clearance_line_ids.state")
    def _compute_clearance_done(self):
        for rec in self:
            rec.clearance_done = bool(rec.clearance_line_ids) and all(
                line.state == "done" for line in rec.clearance_line_ids
            )

    def _check_hr(self):
        """The UI already gates the HR-only buttons via groups=, but
        button visibility is not authorization - once employees can
        write their own resignation records (bpro_ess), nothing would
        stop a crafted RPC call from, say, accepting their own
        resignation. Method-level check, not just view-level."""
        if not (self.env.su or self.env.user.has_group("bpro_base.group_client_hr")):
            raise AccessError("Only HR can perform this step.")

    def action_submit(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError("Only a draft request can be submitted.")
        self.write({"state": "submitted"})

    def action_accept(self):
        self._check_hr()
        for rec in self:
            if rec.state != "submitted":
                raise UserError("Only a submitted request can be accepted.")
            accepted = fields.Date.context_today(rec)
            vals = {
                "state": "accepted",
                "accepted_date": accepted,
            }
            if not rec.last_working_day:
                vals["last_working_day"] = accepted + timedelta(days=rec.notice_days)
            if not rec.service_start_date:
                first_contract = rec.env["hr.contract"].sudo().search(
                    [("employee_id", "=", rec.employee_id.id)],
                    order="date_start asc", limit=1,
                )
                vals["service_start_date"] = first_contract.date_start or False
            rec.write(vals)
            for line_type, name in STANDARD_CLEARANCE_LINES:
                rec.env["bpro.exit.clearance.line"].create({
                    "exit_id": rec.id,
                    "line_type": line_type,
                    "name": name,
                })

    def _current_contract(self):
        self.ensure_one()
        return self.env["hr.contract"].sudo().search(
            [("employee_id", "=", self.employee_id.id), ("state", "=", "open")],
            order="date_start desc", limit=1,
        ) or self.env["hr.contract"].sudo().search(
            [("employee_id", "=", self.employee_id.id)],
            order="date_start desc", limit=1,
        )

    def _el_balance(self):
        """Remaining Earned Leave: validated allocations minus taken
        (approved) leaves for the seeded EL type. Computed directly from
        the source records rather than hr.leave.type's context-dependent
        virtual_remaining_leaves, so the figure is stable and auditable
        on the F&F statement."""
        self.ensure_one()
        el_type = self.env.ref("bpro_leave.leave_type_earned", raise_if_not_found=False)
        if not el_type:
            return 0.0
        allocations = self.env["hr.leave.allocation"].sudo().search([
            ("employee_id", "=", self.employee_id.id),
            ("holiday_status_id", "=", el_type.id),
            ("state", "=", "validate"),
        ])
        taken = self.env["hr.leave"].sudo().search([
            ("employee_id", "=", self.employee_id.id),
            ("holiday_status_id", "=", el_type.id),
            ("state", "=", "validate"),
        ])
        return sum(allocations.mapped("number_of_days")) - sum(taken.mapped("number_of_days"))

    def action_compute_settlement(self):
        self._check_hr()
        for rec in self:
            if rec.state not in ("accepted", "settled"):
                raise UserError("Accept the resignation before computing the settlement.")
            contract = rec._current_contract()
            if not contract:
                raise UserError(f"{rec.employee_id.name} has no contract to settle from.")
            monthly_basic = contract.ctc_annual / 12.0 * (contract.basic_percent / 100.0)

            # Gratuity - Payment of Gratuity Act 1972 s4: 15/26 of
            # monthly wages per completed year of service; a fraction
            # beyond six months counts as a full year; 5-year minimum
            # continuous service; capped (company-configurable ceiling).
            gratuity_years = 0
            gratuity = 0.0
            end = rec.last_working_day or fields.Date.context_today(rec)
            if rec.service_start_date:
                service_days = (end - rec.service_start_date).days
                raw_years = service_days / 365.25
                if raw_years >= 5.0:
                    gratuity_years = int(raw_years)
                    if (raw_years - gratuity_years) > 0.5:
                        gratuity_years += 1
                    gratuity = min(
                        15.0 / 26.0 * monthly_basic * gratuity_years,
                        rec.company_id.gratuity_cap or float("inf"),
                    )

            el_balance = rec._el_balance()
            el_encashment = max(el_balance, 0.0) * monthly_basic / 26.0

            served = (end - rec.accepted_date).days if rec.accepted_date else 0
            shortfall = max(rec.notice_days - served, 0)
            monthly_gross = monthly_basic * (1 + contract.hra_percent / 100.0)
            notice_recovery = shortfall * monthly_gross / 30.0 if shortfall else 0.0

            rec.write({
                "monthly_basic": monthly_basic,
                "gratuity_years": gratuity_years,
                "gratuity_amount": gratuity,
                "el_balance_days": el_balance,
                "el_encashment_amount": el_encashment,
                "notice_shortfall_days": shortfall,
                "notice_recovery_amount": notice_recovery,
                "settlement_computed": True,
            })
            rec._recompute_total()

    def _recompute_total(self):
        for rec in self:
            rec.settlement_total = (
                rec.gratuity_amount
                + rec.el_encashment_amount
                + rec.other_addition
                - rec.notice_recovery_amount
                - rec.other_deduction
            )

    def action_settle(self):
        self._check_hr()
        for rec in self:
            if rec.state != "accepted":
                raise UserError("Only a request in clearance can be settled.")
            if not rec.clearance_done:
                pending = rec.clearance_line_ids.filtered(lambda l: l.state != "done")
                raise UserError(
                    "Clearance incomplete - pending: "
                    + ", ".join(pending.mapped("name"))
                )
            if not rec.settlement_computed:
                rec.action_compute_settlement()
            rec._recompute_total()
        self.write({"state": "settled"})

    def action_close(self):
        """Registers the departure through the native wizard path so
        bpro_hr's login-deactivation override fires - reused, not
        duplicated here."""
        self._check_hr()
        for rec in self:
            if rec.state != "settled":
                raise UserError("Only a settled request can be closed.")
            reason = self.env.ref("hr.departure_resigned", raise_if_not_found=False) \
                or self.env["hr.departure.reason"].sudo().search([], limit=1)
            wizard = self.env["hr.departure.wizard"].sudo().with_context(
                active_id=rec.employee_id.id, toggle_active=True
            ).create({
                "employee_id": rec.employee_id.id,
                "departure_reason_id": reason.id,
                "departure_date": rec.last_working_day or fields.Date.context_today(rec),
                "departure_description": rec.reason or "",
            })
            wizard.action_register_departure()
        self.write({"state": "closed"})


class BproExitClearanceLine(models.Model):
    _name = "bpro.exit.clearance.line"
    _description = "Exit Clearance Line"
    _order = "id"

    exit_id = fields.Many2one("bpro.exit.request", required=True, ondelete="cascade")
    department_id = fields.Many2one(related="exit_id.department_id", store=True)
    name = fields.Char(required=True)
    line_type = fields.Selection(
        [
            ("asset", "Asset Return"),
            ("hod", "HOD Sign-off"),
            ("finance", "Finance Sign-off"),
            ("it", "IT / Access Sign-off"),
            ("other", "Other"),
        ],
        default="other",
        required=True,
        help="'Other' lines are the per-position extras the scoping "
        "answer asked for - add as many as the exit needs.",
    )
    state = fields.Selection(
        [("pending", "Pending"), ("done", "Done")],
        default="pending",
        required=True,
    )
    note = fields.Char()
    done_by = fields.Many2one("res.users", readonly=True, copy=False)
    done_date = fields.Datetime(readonly=True, copy=False)

    def action_mark_done(self):
        for line in self:
            if line.state == "done":
                raise UserError(f"'{line.name}' is already done.")
            if line.line_type == "asset":
                issued = self.env["bpro.employee.asset"].sudo().search([
                    ("employee_id", "=", line.exit_id.employee_id.id),
                    ("state", "=", "issued"),
                ])
                if issued:
                    raise UserError(
                        "Asset clearance blocked - still issued: "
                        + ", ".join(issued.mapped("name"))
                        + ". Mark them returned in the asset register first."
                    )
        self.write({
            "state": "done",
            "done_by": self.env.user.id,
            "done_date": fields.Datetime.now(),
        })
