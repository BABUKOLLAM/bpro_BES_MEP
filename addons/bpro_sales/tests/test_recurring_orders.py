from odoo import fields
from odoo.tests.common import TransactionCase


class TestRecurringOrders(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create(
            {"name": "Recurring Test Widget", "list_price": 50.0}
        )
        cls.partner = cls.env["res.partner"].create({"name": "Recurring Test Customer"})

    def _order(self, interval="monthly"):
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "bpro_is_recurring": True,
                "bpro_recurrence_interval": interval,
                "order_line": [
                    (0, 0, {"product_id": self.product.id, "product_uom_qty": 1})
                ],
            }
        )

    def test_confirming_a_recurring_order_sets_next_renewal_date(self):
        order = self._order()
        order.action_confirm()
        self.assertTrue(order.bpro_next_recurrence_date)

    def test_non_recurring_order_gets_no_renewal_date(self):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    (0, 0, {"product_id": self.product.id, "product_uom_qty": 1})
                ],
            }
        )
        order.action_confirm()
        self.assertFalse(order.bpro_next_recurrence_date)

    def test_cron_ignores_orders_not_yet_due(self):
        order = self._order()
        order.action_confirm()
        # freshly confirmed - next_recurrence_date is in the future, so a
        # same-day cron run must not renew it yet
        self.env["sale.order"]._bpro_cron_generate_recurring_orders()
        self.assertFalse(
            self.env["sale.order"].search(
                [("bpro_recurring_parent_id", "=", order.id)]
            )
        )

    def test_cron_renews_a_due_master_and_advances_its_date(self):
        order = self._order()
        order.action_confirm()
        # simulate time passing: back-date the master to be due today
        backdated_due_date = fields.Date.context_today(order)
        order.bpro_next_recurrence_date = backdated_due_date
        self.env["sale.order"]._bpro_cron_generate_recurring_orders()
        child = self.env["sale.order"].search(
            [("bpro_recurring_parent_id", "=", order.id)]
        )
        self.assertEqual(len(child), 1)
        self.assertEqual(child.state, "sale")
        self.assertFalse(child.bpro_is_recurring)
        self.assertGreater(order.bpro_next_recurrence_date, backdated_due_date)

    def test_rerunning_cron_same_day_does_not_double_renew(self):
        order = self._order()
        order.action_confirm()
        order.bpro_next_recurrence_date = fields.Date.context_today(order)
        self.env["sale.order"]._bpro_cron_generate_recurring_orders()
        self.env["sale.order"]._bpro_cron_generate_recurring_orders()
        children = self.env["sale.order"].search(
            [("bpro_recurring_parent_id", "=", order.id)]
        )
        self.assertEqual(
            len(children),
            1,
            "advancing the master's next-due date past today must stop a "
            "same-day rerun from renewing it twice",
        )
