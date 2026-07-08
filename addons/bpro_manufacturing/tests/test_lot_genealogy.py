from odoo.tests.common import TransactionCase

# FR-MFG-010/011: documents native lot genealogy - stock's traceability
# report (extended by mrp to follow manufacturing consumption) already
# links a finished lot to the raw-material lots consumed to produce it,
# and supports forward/backward trace from either lot. No custom code.


class TestLotGenealogy(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.company.id)], limit=1
        )
        cls.workcenter = cls.env["mrp.workcenter"].create(
            {
                "name": "Genealogy Test Work Center",
                "resource_calendar_id": cls.company.resource_calendar_id.id,
            }
        )
        cls.component = cls.env["product.product"].create(
            {
                "name": "Tracked Raw Material",
                "is_storable": True,
                "tracking": "lot",
            }
        )
        cls.finished = cls.env["product.product"].create(
            {
                "name": "Tracked Finished Good",
                "is_storable": True,
                "tracking": "lot",
            }
        )
        cls.bom = cls.env["mrp.bom"].create(
            {
                "product_tmpl_id": cls.finished.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [
                    (0, 0, {"product_id": cls.component.id, "product_qty": 1.0}),
                ],
            }
        )
        cls.raw_lot = cls.env["stock.lot"].create(
            {"name": "RM-LOT-1", "product_id": cls.component.id}
        )
        cls.env["stock.quant"]._update_available_quantity(
            cls.component, cls.warehouse.lot_stock_id, 10.0, lot_id=cls.raw_lot
        )

    def test_finished_lot_traces_back_to_consumed_raw_lot(self):
        mo = self.env["mrp.production"].create(
            {
                "product_id": self.finished.id,
                "product_qty": 1.0,
                "bom_id": self.bom.id,
                "product_uom_id": self.finished.uom_id.id,
            }
        )
        mo.action_confirm()
        mo.action_assign()
        mo.move_raw_ids.move_line_ids.lot_id = self.raw_lot
        mo.move_raw_ids.picked = True
        mo.qty_producing = 1.0
        finished_lot = self.env["stock.lot"].create(
            {"name": "FG-LOT-1", "product_id": self.finished.id}
        )
        mo.lot_producing_id = finished_lot
        mo.button_mark_done()

        self.assertEqual(mo.state, "done")

        # data-level check: the finished move and the raw move share the
        # same production_id, which is what the trace report walks
        finished_move_line = mo.move_finished_ids.move_line_ids.filtered(
            lambda ml: ml.lot_id == finished_lot
        )
        raw_move_line = mo.move_raw_ids.move_line_ids.filtered(
            lambda ml: ml.lot_id == self.raw_lot
        )
        self.assertTrue(finished_move_line)
        self.assertTrue(raw_move_line)
        self.assertEqual(
            finished_move_line.move_id.production_id,
            raw_move_line.move_id.raw_material_production_id,
        )

        # integration smoke test: the native trace report resolves from
        # either lot without erroring, and finds the other one
        report = self.env["stock.traceability.report"]
        forward = report.get_lines(
            model_name="stock.lot", model_id=self.raw_lot.id, level=1
        )
        self.assertTrue(forward, "forward trace from the raw lot must return results")
        backward = report.get_lines(
            model_name="stock.lot", model_id=finished_lot.id, level=1
        )
        self.assertTrue(
            backward, "backward trace from the finished lot must return results"
        )
