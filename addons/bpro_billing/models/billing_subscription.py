from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class BillingSubscription(models.Model):
    _name = "bpro.billing.subscription"
    _description = "Client Subscription"
    _inherit = ["mail.thread"]
    _rec_name = "client_company_id"

    client_company_id = fields.Many2one(
        "res.company",
        string="Client",
        required=True,
        domain="[('parent_id', '!=', False)]",
        tracking=True,
    )
    plan_id = fields.Many2one("bpro.billing.plan", string="Plan", required=True)
    seats = fields.Integer(
        string="Seats (active employees)", compute="_compute_seats", store=False
    )
    amount = fields.Float(string="Amount per Period", compute="_compute_amount")
    currency_id = fields.Many2one(related="plan_id.currency_id")
    date_start = fields.Date(default=fields.Date.context_today, required=True)
    next_invoice_date = fields.Date(
        string="Next Invoice",
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        [
            ("trial", "Trial"),
            ("active", "Active"),
            ("suspended", "Suspended"),
            ("cancelled", "Cancelled"),
        ],
        default="trial",
        tracking=True,
    )
    invoice_ids = fields.One2many(
        "account.move", "bpro_subscription_id", string="Invoices"
    )
    invoice_count = fields.Integer(compute="_compute_invoice_count")

    _sql_constraints = [
        (
            "client_unique",
            "UNIQUE(client_company_id)",
            "This client already has a subscription.",
        ),
    ]

    @api.depends("client_company_id")
    def _compute_seats(self):
        Employee = self.env["hr.employee"].sudo()
        for sub in self:
            sub.seats = (
                Employee.search_count(
                    [("company_id", "child_of", sub.client_company_id.id)]
                )
                if sub.client_company_id
                else 0
            )

    @api.depends("plan_id", "client_company_id")
    def _compute_amount(self):
        for sub in self:
            sub.amount = sub.seats * sub.plan_id.price_per_seat

    def _compute_invoice_count(self):
        for sub in self:
            sub.invoice_count = len(sub.invoice_ids)

    def action_activate(self):
        return self.write({"state": "active"})

    def action_suspend(self):
        return self.write({"state": "suspended"})

    def action_cancel(self):
        return self.write({"state": "cancelled"})

    def action_invoice_now(self):
        self._create_period_invoice()
        return True

    def action_view_invoices(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Invoices",
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("bpro_subscription_id", "=", self.id)],
        }

    def _create_period_invoice(self):
        """Raise a draft invoice for the current period and roll the
        next invoice date forward."""
        for sub in self:
            if sub.state not in ("trial", "active"):
                continue
            if not sub.client_company_id.partner_id:
                raise UserError(
                    f"Client {sub.client_company_id.name} has no partner record."
                )
            seats = sub.seats
            label = (
                f"bpro LMS + PMS — {sub.plan_id.name} "
                f"({seats} seats, {sub.plan_id.period})"
            )
            self.env["account.move"].sudo().create(
                {
                    "move_type": "out_invoice",
                    "partner_id": sub.client_company_id.partner_id.id,
                    "invoice_date": sub.next_invoice_date,
                    "bpro_subscription_id": sub.id,
                    "invoice_line_ids": [
                        (
                            0,
                            0,
                            {
                                "name": label,
                                "quantity": seats,
                                "price_unit": sub.plan_id.price_per_seat,
                            },
                        )
                    ],
                }
            )
            months = 1 if sub.plan_id.period == "monthly" else 12
            sub.write(
                {
                    "next_invoice_date": sub.next_invoice_date
                    + relativedelta(months=months),
                    "state": "active",
                }
            )

    @api.model
    def _cron_generate_invoices(self):
        due = self.search(
            [
                ("state", "in", ("trial", "active")),
                ("next_invoice_date", "<=", fields.Date.context_today(self)),
            ]
        )
        due._create_period_invoice()


class AccountMove(models.Model):
    _inherit = "account.move"

    bpro_subscription_id = fields.Many2one(
        "bpro.billing.subscription", string="bpro Subscription", index=True
    )
