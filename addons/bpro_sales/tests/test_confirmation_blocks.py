from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestCreditLimitBlock(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.company.account_use_credit_limit = True
        cls.product = cls.env["product.product"].create(
            {"name": "Credit Test Widget", "list_price": 1000.0}
        )
        cls.partner = cls.env["res.partner"].create(
            {"name": "Credit Test Customer", "credit_limit": 500.0}
        )

    def _order(self, price_unit):
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 1,
                            "price_unit": price_unit,
                            "tax_id": False,
                        },
                    )
                ],
            }
        )

    def test_order_within_credit_limit_confirms(self):
        order = self._order(400.0)
        order.action_confirm()
        self.assertEqual(order.state, "sale")

    def test_order_exceeding_credit_limit_is_blocked(self):
        order = self._order(600.0)
        with self.assertRaises(UserError):
            order.action_confirm()
        self.assertEqual(order.state, "draft")


class TestStockShortageBlock(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.company.id)], limit=1
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Stock Shortage Test Widget", "is_storable": True}
        )
        cls.partner = cls.env["res.partner"].create({"name": "Stock Shortage Customer"})

    def _order(self, qty):
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": self.warehouse.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": qty,
                            "price_unit": 10.0,
                            "tax_id": False,
                        },
                    )
                ],
            }
        )

    def test_order_within_available_stock_confirms(self):
        self.env["stock.quant"]._update_available_quantity(
            self.product, self.warehouse.lot_stock_id, 10.0
        )
        order = self._order(5.0)
        order.action_confirm()
        self.assertEqual(order.state, "sale")

    def test_order_exceeding_available_stock_is_blocked(self):
        self.env["stock.quant"]._update_available_quantity(
            self.product, self.warehouse.lot_stock_id, 3.0
        )
        order = self._order(5.0)
        with self.assertRaises(UserError):
            order.action_confirm()
        self.assertEqual(order.state, "draft")
