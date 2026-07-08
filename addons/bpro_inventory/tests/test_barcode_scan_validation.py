from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestBarcodeScanValidation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.company.id)], limit=1
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Scan Test Product",
                "is_storable": True,
                "barcode": "SCANTEST001",
                "default_code": "SCN-001",
            }
        )
        cls.env["stock.quant"]._update_available_quantity(
            cls.product, cls.warehouse.lot_stock_id, 10.0
        )

    def _receipt_move(self):
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.warehouse.in_type_id.id,
                "location_id": self.env.ref("stock.stock_location_suppliers").id,
                "location_dest_id": self.warehouse.lot_stock_id.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "name": self.product.name,
                            "product_id": self.product.id,
                            "product_uom_qty": 5.0,
                            "product_uom": self.product.uom_id.id,
                            "location_id": self.env.ref(
                                "stock.stock_location_suppliers"
                            ).id,
                            "location_dest_id": self.warehouse.lot_stock_id.id,
                        },
                    )
                ],
            }
        )
        return picking.move_ids

    def test_no_scan_entered_is_unaffected(self):
        move = self._receipt_move()
        move.write({"quantity": 5.0})
        self.assertFalse(move.bpro_scanned_code)

    def test_scanning_the_barcode_succeeds(self):
        move = self._receipt_move()
        move.write({"bpro_scanned_code": "SCANTEST001"})
        self.assertEqual(move.bpro_scanned_code, "SCANTEST001")

    def test_scanning_the_internal_reference_succeeds(self):
        move = self._receipt_move()
        move.write({"bpro_scanned_code": "SCN-001"})
        self.assertEqual(move.bpro_scanned_code, "SCN-001")

    def test_scanning_a_mismatched_code_is_rejected(self):
        move = self._receipt_move()
        with self.assertRaises(UserError):
            move.write({"bpro_scanned_code": "WRONG-CODE"})

    def test_scanning_the_lot_number_succeeds(self):
        tracked_product = self.env["product.product"].create(
            {
                "name": "Scan Test Tracked Product",
                "is_storable": True,
                "tracking": "lot",
                "barcode": "SCANTRACKED001",
            }
        )
        lot = self.env["stock.lot"].create(
            {"name": "LOT-XYZ", "product_id": tracked_product.id}
        )
        self.env["stock.quant"]._update_available_quantity(
            tracked_product, self.warehouse.lot_stock_id, 5.0, lot_id=lot
        )
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.warehouse.in_type_id.id,
                "location_id": self.env.ref("stock.stock_location_suppliers").id,
                "location_dest_id": self.warehouse.lot_stock_id.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "name": tracked_product.name,
                            "product_id": tracked_product.id,
                            "product_uom_qty": 5.0,
                            "product_uom": tracked_product.uom_id.id,
                            "location_id": self.env.ref(
                                "stock.stock_location_suppliers"
                            ).id,
                            "location_dest_id": self.warehouse.lot_stock_id.id,
                            "move_line_ids": [
                                (
                                    0,
                                    0,
                                    {
                                        "product_id": tracked_product.id,
                                        "lot_id": lot.id,
                                        "quantity": 5.0,
                                        "location_id": self.env.ref(
                                            "stock.stock_location_suppliers"
                                        ).id,
                                        "location_dest_id": self.warehouse.lot_stock_id.id,
                                    },
                                )
                            ],
                        },
                    )
                ],
            }
        )
        move = picking.move_ids
        move.write({"bpro_scanned_code": "LOT-XYZ"})
        self.assertEqual(move.bpro_scanned_code, "LOT-XYZ")

    def test_scanning_does_not_block_picking_validation_when_correct(self):
        move = self._receipt_move()
        move.write({"bpro_scanned_code": "SCANTEST001"})
        picking = move.picking_id
        picking.action_confirm()
        picking.action_assign()
        move.quantity = 5.0
        move.picked = True
        picking.button_validate()
        self.assertEqual(picking.state, "done")
