from odoo.tests.common import TransactionCase


class TestEquipmentMaintenance(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.workcenter = cls.env["mrp.workcenter"].create({"name": "Plant Test Workcenter"})
        cls.equipment = cls.env["maintenance.equipment"].create(
            {"name": "Plant Test Machine", "workcenter_id": cls.workcenter.id}
        )
        cls.component = cls.env["product.product"].create(
            {"name": "Plant Test Component", "is_storable": True}
        )
        cls.finished = cls.env["product.product"].create(
            {"name": "Plant Test Finished Good", "is_storable": True}
        )
        cls.bom = cls.env["mrp.bom"].create(
            {
                "product_tmpl_id": cls.finished.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [(0, 0, {"product_id": cls.component.id, "product_qty": 1.0})],
                "operation_ids": [
                    (0, 0, {"name": "Assemble", "workcenter_id": cls.workcenter.id}),
                ],
            }
        )
        warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.ref("base.main_company").id)], limit=1
        )
        cls.env["stock.quant"]._update_available_quantity(
            cls.component, warehouse.lot_stock_id, 100.0
        )

    def _mo(self):
        return self.env["mrp.production"].create(
            {
                "product_id": self.finished.id,
                "product_qty": 1.0,
                "bom_id": self.bom.id,
                "product_uom_id": self.finished.uom_id.id,
            }
        )

    def test_equipment_shows_up_on_its_workcenter(self):
        self.assertIn(self.equipment, self.workcenter.bpro_equipment_ids)

    def test_no_open_request_means_no_warning(self):
        mo = self._mo()
        mo.action_confirm()
        wo = mo.workorder_ids
        self.assertFalse(wo.bpro_plant_maintenance_warning)

    def test_open_corrective_request_warns_on_the_workorder(self):
        self.env["maintenance.request"].create(
            {
                "name": "Bearing noise",
                "equipment_id": self.equipment.id,
                "maintenance_type": "corrective",
            }
        )
        mo = self._mo()
        mo.action_confirm()
        wo = mo.workorder_ids
        self.assertIn(self.equipment.name, wo.bpro_plant_maintenance_warning)

    def test_resolving_the_request_clears_the_warning(self):
        request = self.env["maintenance.request"].create(
            {
                "name": "Bearing noise",
                "equipment_id": self.equipment.id,
                "maintenance_type": "corrective",
            }
        )
        mo = self._mo()
        mo.action_confirm()
        wo = mo.workorder_ids
        self.assertTrue(wo.bpro_plant_maintenance_warning)
        request.stage_id = self.env.ref("maintenance.stage_3")
        self.assertFalse(wo.bpro_plant_maintenance_warning)

    def test_preventive_request_does_not_warn(self):
        self.env["maintenance.request"].create(
            {
                "name": "Scheduled lubrication",
                "equipment_id": self.equipment.id,
                "maintenance_type": "preventive",
            }
        )
        mo = self._mo()
        mo.action_confirm()
        wo = mo.workorder_ids
        self.assertFalse(wo.bpro_plant_maintenance_warning)

    def test_downtime_hours_computed_on_closed_corrective_request(self):
        request = self.env["maintenance.request"].create(
            {
                "name": "Motor replacement",
                "equipment_id": self.equipment.id,
                "maintenance_type": "corrective",
                "request_date": "2026-01-01",
            }
        )
        request.stage_id = self.env.ref("maintenance.stage_3")
        request.close_date = "2026-01-03"
        self.assertEqual(request.bpro_downtime_hours, 48.0)

    def test_downtime_hours_zero_for_preventive(self):
        request = self.env["maintenance.request"].create(
            {
                "name": "Scheduled check",
                "equipment_id": self.equipment.id,
                "maintenance_type": "preventive",
                "request_date": "2026-01-01",
            }
        )
        request.stage_id = self.env.ref("maintenance.stage_3")
        request.close_date = "2026-01-03"
        self.assertEqual(request.bpro_downtime_hours, 0.0)
