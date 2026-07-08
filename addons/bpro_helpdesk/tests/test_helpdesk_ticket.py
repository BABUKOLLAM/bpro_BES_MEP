from odoo.tests.common import TransactionCase


class TestHelpdeskTicket(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.partner = cls.env["res.partner"].create({"name": "Helpdesk Test Customer"})
        cls.new_stage = cls.env.ref("bpro_helpdesk.helpdesk_stage_new")
        cls.resolved_stage = cls.env.ref("bpro_helpdesk.helpdesk_stage_resolved")

    def _ticket(self, **overrides):
        vals = {"name": "Test issue", "partner_id": self.partner.id}
        vals.update(overrides)
        return self.env["bpro.helpdesk.ticket"].create(vals)

    def test_new_ticket_defaults_to_new_stage(self):
        ticket = self._ticket()
        self.assertEqual(ticket.stage_id, self.new_stage)
        self.assertFalse(ticket.is_closed)

    def test_sla_deadline_uses_configured_response_hours(self):
        self.env["bpro.policy"].create(
            {
                "company_id": self.company.id,
                "key": "helpdesk_sla_response_hours",
                "numeric_value": 24.0,
            }
        )
        ticket = self._ticket()
        self.assertAlmostEqual(
            (ticket.sla_deadline - ticket.create_date).total_seconds() / 3600.0,
            24.0,
            places=2,
        )

    def test_ticket_already_past_deadline_is_overdue(self):
        self.env["bpro.policy"].create(
            {
                "company_id": self.company.id,
                "key": "helpdesk_sla_response_hours",
                "numeric_value": -1.0,
            }
        )
        ticket = self._ticket()
        self.assertTrue(ticket.is_overdue)

    def test_ticket_within_window_is_not_overdue(self):
        self.env["bpro.policy"].create(
            {
                "company_id": self.company.id,
                "key": "helpdesk_sla_response_hours",
                "numeric_value": 24.0,
            }
        )
        ticket = self._ticket()
        self.assertFalse(ticket.is_overdue)

    def test_closing_an_overdue_ticket_clears_the_overdue_flag(self):
        self.env["bpro.policy"].create(
            {
                "company_id": self.company.id,
                "key": "helpdesk_sla_response_hours",
                "numeric_value": -1.0,
            }
        )
        ticket = self._ticket()
        self.assertTrue(ticket.is_overdue)
        ticket.action_bpro_close()
        self.assertFalse(ticket.is_overdue)

    def test_closing_a_ticket_sets_close_date_and_resolution_hours(self):
        ticket = self._ticket()
        self.assertFalse(ticket.close_date)
        ticket.action_bpro_close()
        self.assertTrue(ticket.close_date)
        self.assertGreaterEqual(ticket.resolution_hours, 0.0)

    def test_reopening_a_closed_ticket_clears_close_date(self):
        ticket = self._ticket()
        ticket.action_bpro_close()
        self.assertTrue(ticket.close_date)
        ticket.stage_id = self.new_stage
        self.assertFalse(ticket.close_date)
        self.assertEqual(ticket.resolution_hours, 0.0)

    def test_ticket_can_link_to_a_sale_order(self):
        product = self.env["product.product"].create(
            {"name": "Helpdesk Test Product", "list_price": 100.0}
        )
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    (0, 0, {"product_id": product.id, "product_uom_qty": 1})
                ],
            }
        )
        ticket = self._ticket(sale_order_id=order.id)
        self.assertEqual(ticket.sale_order_id, order)

    def test_team_ticket_count(self):
        team = self.env["bpro.helpdesk.team"].create({"name": "Test Team"})
        self._ticket(team_id=team.id)
        self._ticket(team_id=team.id)
        self.assertEqual(team.ticket_count, 2)
