from psycopg2 import IntegrityError

from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestSalesArea(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.product = cls.env["product.product"].create(
            {"name": "Sales Area Test Widget", "list_price": 100.0}
        )
        cls.partner = cls.env["res.partner"].create({"name": "Sales Area Test Customer"})
        cls.area = cls.env["bpro.sales.area"].create({"name": "EKM"})

    def test_area_can_be_set_on_order(self):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "sales_area_id": self.area.id,
                "order_line": [
                    (0, 0, {"product_id": self.product.id, "product_uom_qty": 1})
                ],
            }
        )
        self.assertEqual(order.sales_area_id, self.area)

    def test_duplicate_area_name_same_company_blocked(self):
        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"):
            self.env["bpro.sales.area"].create({"name": "EKM"})

    def test_employee_coverage_areas(self):
        area2 = self.env["bpro.sales.area"].create({"name": "KNNR"})
        employee = self.env["hr.employee"].create(
            {
                "name": "Field Rep Test",
                "bpro_sales_area_ids": [(6, 0, [self.area.id, area2.id])],
            }
        )
        self.assertEqual(len(employee.bpro_sales_area_ids), 2)
