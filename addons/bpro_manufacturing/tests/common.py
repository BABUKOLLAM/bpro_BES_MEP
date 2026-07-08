from odoo.tests.common import TransactionCase


class MfgTestCommon(TransactionCase):
    """Shared BOM/workcenter/stock fixture for bpro_manufacturing tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.company.id)], limit=1
        )
        cls.workcenter = cls.env["mrp.workcenter"].create(
            {
                "name": "Test Work Center",
                "resource_calendar_id": cls.company.resource_calendar_id.id,
                "default_capacity": 1,
            }
        )
        cls.component = cls.env["product.product"].create(
            {"name": "Raw Material", "is_storable": True}
        )
        cls.finished = cls.env["product.product"].create(
            {"name": "Finished Good", "is_storable": True}
        )
        cls.bom = cls.env["mrp.bom"].create(
            {
                "product_tmpl_id": cls.finished.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [
                    (0, 0, {"product_id": cls.component.id, "product_qty": 2.0}),
                ],
                "operation_ids": [
                    (0, 0, {"name": "Assemble", "workcenter_id": cls.workcenter.id}),
                ],
            }
        )
        cls.env["stock.quant"]._update_available_quantity(
            cls.component, cls.warehouse.lot_stock_id, 1000.0
        )

    def _mo(self, qty=1.0):
        return self.env["mrp.production"].create(
            {
                "product_id": self.finished.id,
                "product_qty": qty,
                "bom_id": self.bom.id,
                "product_uom_id": self.finished.uom_id.id,
            }
        )
