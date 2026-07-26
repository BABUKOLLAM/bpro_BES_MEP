from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestWeeklyMis(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.today = fields.Date.context_today(cls.env.user)
        cls.workcenter = cls.env["mrp.workcenter"].create({"name": "MIS Workcenter"})

    def _mis(self, as_of_date=None):
        return self.env["bpro.executive.dashboard"]._get_weekly_mis_data(
            self.company, as_of_date or self.today
        )

    def _make_done_workorder(self, product, qty, finished_date):
        component = self.env["product.product"].create(
            {"name": f"{product.name} component", "is_storable": True}
        )
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": product.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [(0, 0, {"product_id": component.id, "product_qty": 1.0})],
                "operation_ids": [(0, 0, {"name": "Make", "workcenter_id": self.workcenter.id})],
            }
        )
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.company.id)], limit=1
        )
        self.env["stock.quant"]._update_available_quantity(
            component, warehouse.lot_stock_id, 1000.0
        )
        mo = self.env["mrp.production"].create(
            {
                "product_id": product.id,
                "product_qty": qty,
                "bom_id": bom.id,
                "product_uom_id": product.uom_id.id,
            }
        )
        mo.action_confirm()
        mo.workorder_ids.write(
            {"qty_produced": qty, "state": "done", "date_finished": finished_date}
        )
        return mo.workorder_ids

    def _confirmed_order(self, product, qty, price, order_date, area=None):
        partner = self.env["res.partner"].create({"name": "MIS Test Customer"})
        order = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "sales_area_id": area.id if area else False,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_uom_qty": qty,
                            "price_unit": price,
                            "tax_id": False,
                        },
                    )
                ],
            }
        )
        order.action_confirm()
        order.date_order = order_date
        return order

    def test_no_data_gives_zeroes_and_no_errors(self):
        other_company = self.env["res.company"].create({"name": "Empty MIS Co"})
        data = self.env["bpro.executive.dashboard"]._get_weekly_mis_data(
            other_company, self.today
        )
        self.assertEqual(data["weekly_production_qty"], 0.0)
        self.assertEqual(data["production_wow_pct"], 0.0)
        self.assertEqual(data["weekly_sales_amount"], 0.0)
        self.assertEqual(data["sales_wow_pct"], 0.0)
        self.assertEqual(data["item_production_lines"], [])
        self.assertEqual(data["item_sales_lines"], [])
        self.assertEqual(data["area_sales_lines"], [])

    def test_weekly_production_qty_and_wow_pct(self):
        product = self.env["product.product"].create(
            {"name": "MIS Prod Widget", "is_storable": True}
        )
        # this week
        self._make_done_workorder(product, 100.0, self.today)
        # previous week (8 days back, safely inside the prior 7-day window)
        self._make_done_workorder(
            product, 50.0, fields.Datetime.to_datetime(self.today) - timedelta(days=8)
        )
        data = self._mis()
        self.assertEqual(data["weekly_production_qty"], 100.0)
        self.assertEqual(data["production_wow_pct"], 100.0)  # 100 vs 50 = +100%

    def test_weekly_sales_amount_and_wow_pct(self):
        product = self.env["product.product"].create({"name": "MIS Sale Widget"})
        self._confirmed_order(product, 1, 1000.0, f"{self.today} 10:00:00")
        prev_week_date = fields.Date.to_string(self.today - timedelta(days=8))
        self._confirmed_order(product, 1, 500.0, f"{prev_week_date} 10:00:00")
        data = self._mis()
        self.assertEqual(data["weekly_sales_amount"], 1000.0)
        self.assertEqual(data["sales_wow_pct"], 100.0)  # 1000 vs 500 = +100%

    def test_item_production_line_achieved_vs_target(self):
        product = self.env["product.product"].create(
            {"name": "MIS Target Widget", "is_storable": True}
        )
        self._make_done_workorder(product, 80.0, self.today)
        self.env["bpro.item.target"].create(
            {
                "product_id": product.id,
                "company_id": self.company.id,
                "monthly_production_qty_target": 100.0,
            }
        )
        lines = self._mis()["item_production_lines"]
        self.assertEqual(len(lines), 1)
        line = lines[0]
        self.assertEqual(line["achieved"], 80.0)
        self.assertEqual(line["target"], 100.0)
        self.assertEqual(line["balance"], -20.0)
        self.assertEqual(line["achievement_pct"], 80.0)

    def test_item_sales_line_actual_vs_target(self):
        product = self.env["product.product"].create({"name": "MIS Sale Target Widget"})
        self._confirmed_order(product, 30, 10.0, f"{self.today} 10:00:00")
        self.env["bpro.item.target"].create(
            {
                "product_id": product.id,
                "company_id": self.company.id,
                "weekly_sales_qty_target": 100.0,
            }
        )
        lines = self._mis()["item_sales_lines"]
        self.assertEqual(len(lines), 1)
        line = lines[0]
        self.assertEqual(line["actual"], 30.0)
        self.assertEqual(line["target"], 100.0)
        self.assertEqual(line["diff"], -70.0)
        self.assertEqual(line["achievement_pct"], 30.0)

    def test_area_wise_sales_order_count(self):
        product = self.env["product.product"].create({"name": "MIS Area Widget"})
        area = self.env["bpro.sales.area"].create({"name": "MIS Test Area", "company_id": self.company.id})
        self._confirmed_order(product, 1, 100.0, f"{self.today} 10:00:00", area=area)
        self._confirmed_order(product, 1, 100.0, f"{self.today} 11:00:00", area=area)
        lines = self._mis()["area_sales_lines"]
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["sales_area_id"], area.id)
        self.assertEqual(lines[0]["order_count"], 2)
