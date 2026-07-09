from datetime import timedelta

from odoo import api, fields, models


class BproCollectionsCase(models.Model):
    _name = "bpro.collections.case"
    _description = "Collections Case"
    _order = "days_overdue desc, id desc"

    partner_id = fields.Many2one("res.partner", required=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    overdue_amount = fields.Monetary(readonly=True)
    oldest_overdue_date = fields.Date(readonly=True)
    days_overdue = fields.Integer(readonly=True)
    level = fields.Selection(
        [
            ("reminder", "Reminder"),
            ("firm", "Firm Notice"),
            ("final", "Final Notice"),
        ],
        readonly=True,
    )
    last_contacted_date = fields.Date()
    next_action_date = fields.Date()
    assigned_to = fields.Many2one("res.users")
    notes = fields.Text()
    state = fields.Selection(
        [("open", "Open"), ("closed", "Closed")], default="open", required=True
    )

    _sql_constraints = [
        (
            "partner_company_unique",
            "UNIQUE(partner_id, company_id)",
            "Only one collections case may exist per customer per company.",
        ),
    ]

    @api.model
    def _bpro_overdue_by_partner(self, company, as_of_date):
        """(partner, overdue_amount, oldest_overdue_date) for every partner with
        a positive overdue receivable balance - same filter bpro_finance's AR
        Aging report uses, restricted to lines actually past their due date."""
        move_lines = self.env["account.move.line"].search(
            [
                ("company_id", "=", company.id),
                ("account_id.account_type", "=", "asset_receivable"),
                ("parent_state", "=", "posted"),
                ("reconciled", "=", False),
            ]
        )
        by_partner = {}
        for line in move_lines:
            residual = line.amount_residual
            due_date = line.date_maturity or line.date
            if not residual or due_date >= as_of_date:
                continue
            entry = by_partner.setdefault(line.partner_id, {"amount": 0.0, "oldest": due_date})
            entry["amount"] += residual
            entry["oldest"] = min(entry["oldest"], due_date)
        return by_partner

    def _bpro_level_for_days(self, days):
        """None below the level1 grace period - not yet a collections
        concern, so no case should be opened/kept for it."""
        level1 = self.env["bpro.policy"].get_value(
            self.company_id, "collections_level1_days", 15
        )
        level2 = self.env["bpro.policy"].get_value(
            self.company_id, "collections_level2_days", 30
        )
        level3 = self.env["bpro.policy"].get_value(
            self.company_id, "collections_level3_days", 60
        )
        if days >= level3:
            return "final"
        if days >= level2:
            return "firm"
        if days >= level1:
            return "reminder"
        return None

    @api.model
    def _bpro_sync_cases(self, company=None):
        """Open/update a case for every customer with an overdue balance,
        and close any case whose balance has since cleared. Called by the
        nightly cron and by the manual Refresh button - always a full
        resync for the company, never a partial/incremental update."""
        company = company or self.env.company
        today = fields.Date.context_today(self)
        overdue_by_partner = self._bpro_overdue_by_partner(company, today)

        existing = self.search([("company_id", "=", company.id)])
        existing_by_partner = {case.partner_id: case for case in existing}

        past_grace_period = set()
        for partner, data in overdue_by_partner.items():
            days = (today - data["oldest"]).days
            case = existing_by_partner.get(partner) or self.new(
                {"company_id": company.id}
            )
            level = case._bpro_level_for_days(days)
            if not level:
                continue
            past_grace_period.add(partner)
            vals = {
                "overdue_amount": data["amount"],
                "oldest_overdue_date": data["oldest"],
                "days_overdue": days,
                "level": level,
                "state": "open",
            }
            existing_case = existing_by_partner.get(partner)
            if existing_case:
                existing_case.write(vals)
            else:
                self.create({"partner_id": partner.id, "company_id": company.id, **vals})

        cleared = existing.filtered(
            lambda c: c.state == "open" and c.partner_id not in past_grace_period
        )
        cleared.write({"state": "closed", "overdue_amount": 0.0, "days_overdue": 0})

    def action_refresh(self):
        companies = self.mapped("company_id")
        for company in companies:
            self._bpro_sync_cases(company)

    def action_record_contact(self):
        followup_days = self.env["bpro.policy"].get_value(
            self.env.company, "collections_followup_days", 7
        )
        today = fields.Date.context_today(self)
        for case in self:
            case.write(
                {
                    "last_contacted_date": today,
                    "next_action_date": today + timedelta(days=int(followup_days)),
                }
            )

    def action_close(self):
        self.write({"state": "closed"})

    def action_reopen(self):
        self.write({"state": "open"})
