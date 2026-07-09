from odoo import api, fields, models


class BproFieldCollectionPlan(models.Model):
    _name = "bpro.field.collection.plan"
    _description = "Field Sales Collection Plan"
    _order = "planned_date desc, id desc"

    employee_id = fields.Many2one("hr.employee", required=True, string="Salesperson")
    partner_id = fields.Many2one("res.partner", required=True, string="Dealer/Distributor")
    planned_date = fields.Date(required=True, default=fields.Date.context_today)
    expected_amount = fields.Monetary(required=True)
    collected_amount = fields.Monetary()
    partner_outstanding = fields.Monetary(
        related="partner_id.credit", string="Current Outstanding (live)"
    )
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id
    )
    state = fields.Selection(
        [
            ("planned", "Planned"),
            ("collected", "Collected"),
            ("partial", "Partially Collected"),
            ("missed", "Missed"),
        ],
        default="planned",
        required=True,
    )
    notes = fields.Text()
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )

    def action_confirm_collection(self):
        for plan in self:
            if plan.collected_amount >= plan.expected_amount and plan.collected_amount > 0:
                plan.state = "collected"
            elif plan.collected_amount > 0:
                plan.state = "partial"
            else:
                plan.state = "missed"

    def action_mark_missed(self):
        self.write({"state": "missed", "collected_amount": 0})
