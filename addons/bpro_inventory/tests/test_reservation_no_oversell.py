from odoo.tests.common import TransactionCase

# FR-INV-011/012: real-time allocation, no oversell. This does not spin up
# real concurrent DB transactions (Odoo's TransactionCase runs in a single
# transaction with savepoints, so true concurrency isn't reproducible
# here) - it documents the accounting invariant that makes the native
# reservation system safe under concurrency: reserved quantity can never
# exceed on-hand quantity, because _action_assign() reserves against the
# same quant rows every caller reads, inside the DB's normal row-level
# locking. Real concurrent-load verification belongs in the deferred
# NFR-INV-004 load test, not here.


class TestReservationNoOversell(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.company.id)], limit=1
        )
        cls.customer_location = cls.env.ref("stock.stock_location_customers")
        cls.product = cls.env["product.product"].create(
            {"name": "Reservation Test Widget", "is_storable": True}
        )
        cls.env["stock.quant"]._update_available_quantity(
            cls.product, cls.warehouse.lot_stock_id, 10.0
        )

    def _outgoing_move(self, qty):
        return self.env["stock.move"].create(
            {
                "name": "Test delivery",
                "product_id": self.product.id,
                "product_uom_qty": qty,
                "product_uom": self.product.uom_id.id,
                "location_id": self.warehouse.lot_stock_id.id,
                "location_dest_id": self.customer_location.id,
                "warehouse_id": self.warehouse.id,
            }
        )

    def test_second_reservation_cannot_exceed_remaining_stock(self):
        move_a = self._outgoing_move(8.0)
        move_b = self._outgoing_move(8.0)
        (move_a | move_b)._action_confirm()

        move_a._action_assign()
        self.assertEqual(
            move_a.product_uom_qty,
            move_a.quantity,
            "the first mover for 8 of 10 on hand must reserve in full",
        )

        move_b._action_assign()
        total_reserved = move_a.quantity + move_b.quantity
        self.assertLessEqual(
            total_reserved,
            10.0,
            "reserved quantity across both moves must never exceed on-hand stock",
        )
        self.assertLess(
            move_b.quantity,
            8.0,
            "the second mover must only get the 2 units left, not oversell into move_a's reservation",
        )
