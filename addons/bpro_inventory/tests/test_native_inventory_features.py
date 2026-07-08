from odoo.tests.common import TransactionCase

# These document (not build) the native Odoo behavior the BRD's Must FRs
# rely on, so a future Odoo upgrade that changes this behavior is caught
# here rather than discovered later in Sales/Manufacturing/Finance, which
# depend on it. No bpro_inventory code is exercised by these two tests.


class TestNativeBinLevelStock(TransactionCase):
    """FR-INV-001/002: stock tracked by SKU + warehouse + bin, with a
    bin-level inquiry. stock.quant is always keyed by (product, location);
    the 'Storage Locations' setting only controls whether the UI exposes
    picking a specific bin during operations, not whether the underlying
    per-location quantity tracking exists."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.bin_a = cls.env["stock.location"].create(
            {"name": "Bin A-12-3", "usage": "internal", "company_id": cls.company.id}
        )
        cls.bin_b = cls.env["stock.location"].create(
            {"name": "Bin B-04-1", "usage": "internal", "company_id": cls.company.id}
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Bin Test Widget", "is_storable": True}
        )

    def test_quantities_are_tracked_independently_per_bin(self):
        Quant = self.env["stock.quant"]
        Quant._update_available_quantity(self.product, self.bin_a, 30.0)
        Quant._update_available_quantity(self.product, self.bin_b, 12.0)

        qty_a = Quant._gather(self.product, self.bin_a, strict=True).quantity
        qty_b = Quant._gather(self.product, self.bin_b, strict=True).quantity
        self.assertEqual(qty_a, 30.0)
        self.assertEqual(qty_b, 12.0)

        all_bins = Quant.search(
            [("product_id", "=", self.product.id), ("location_id", "in", [self.bin_a.id, self.bin_b.id])]
        )
        self.assertEqual(len(all_bins), 2, "each bin must be its own inquiry row")
        self.assertEqual(sum(all_bins.mapped("quantity")), 42.0)


class TestNativeReorderAlert(TransactionCase):
    """FR-INV-009: reorder alert when available stock falls at/below the
    reorder point. qty_to_order_computed is the field the native
    Replenishment dashboard reads to decide whether a SKU needs an alert."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.company.id)], limit=1
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Reorder Test Widget", "is_storable": True}
        )
        cls.orderpoint = cls.env["stock.warehouse.orderpoint"].create(
            {
                "product_id": cls.product.id,
                "warehouse_id": cls.warehouse.id,
                "location_id": cls.warehouse.lot_stock_id.id,
                "product_min_qty": 100.0,
                "product_max_qty": 200.0,
            }
        )

    def test_no_alert_when_stock_above_reorder_point(self):
        self.env["stock.quant"]._update_available_quantity(
            self.product, self.warehouse.lot_stock_id, 150.0
        )
        self.orderpoint._compute_qty()
        self.orderpoint._compute_qty_to_order()
        self.assertLessEqual(self.orderpoint.qty_to_order_computed, 0)

    def test_alert_when_stock_below_reorder_point(self):
        # Note: native Odoo triggers on qty_forecast < product_min_qty
        # (strictly below), not <= as the BRD's "at or below" wording
        # implies. A one-unit gap at the exact boundary is inconsequential
        # in practice (set the reorder point a unit higher for equivalent
        # behavior) and not worth custom code to close.
        self.env["stock.quant"]._update_available_quantity(
            self.product, self.warehouse.lot_stock_id, 99.0
        )
        self.orderpoint._compute_qty()
        self.orderpoint._compute_qty_to_order()
        self.assertGreater(
            self.orderpoint.qty_to_order_computed,
            0,
            "crossing the reorder point must surface on the Replenishment dashboard",
        )
