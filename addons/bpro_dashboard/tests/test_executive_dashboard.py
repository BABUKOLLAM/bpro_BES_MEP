from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestExecutiveDashboard(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")

    def _kpi(self):
        today = fields.Date.context_today(self.env.user)
        return self.env["bpro.executive.dashboard"]._get_kpi_data(self.company, today)

    def test_no_data_gives_zeroes_and_no_errors(self):
        other_company = self.env["res.company"].create({"name": "Empty KPI Co"})
        today = fields.Date.context_today(self.env.user)
        data = self.env["bpro.executive.dashboard"]._get_kpi_data(other_company, today)
        self.assertEqual(data["sales_mtd_revenue"], 0.0)
        self.assertEqual(data["mfg_avg_variance_pct"], 0.0)
        self.assertEqual(data["inventory_pending_adjustments"], 0)
        self.assertEqual(data["hr_pending_expense_approvals"], 0)
        self.assertEqual(data["logistics_on_time_pct"], 0.0)
        self.assertEqual(data["quality_pass_rate_pct"], 0.0)
        self.assertEqual(data["plant_total_asset_book_value"], 0.0)
        self.assertEqual(data["project_pending_budget_approvals"], 0)
        self.assertEqual(data["fleet_trip_cost"], 0.0)

    def test_sales_mtd_revenue(self):
        partner = self.env["res.partner"].create({"name": "Dashboard Test Customer"})
        product = self.env["product.product"].create(
            {"name": "Dashboard Test Product", "list_price": 500.0}
        )
        order = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "order_line": [
                    (0, 0, {"product_id": product.id, "product_uom_qty": 2})
                ],
            }
        )
        order.action_confirm()
        self.assertEqual(self._kpi()["sales_mtd_revenue"], order.amount_total)

    def test_sales_mtd_revenue_converts_a_foreign_currency_order(self):
        """An order in a currency other than the company's own must be
        converted before being summed into the KPI, not added raw -
        otherwise a single mixed-currency order corrupts the whole
        month's total rather than just being mislabeled."""
        foreign_currency = self.env.ref("base.EUR")
        foreign_currency.active = True
        self.env["res.currency.rate"].create(
            {
                "currency_id": foreign_currency.id,
                "company_id": self.company.id,
                "name": fields.Date.context_today(self.env.user),
                "rate": 2.0,  # 1 company-currency unit = 2 EUR, i.e. EUR100 = 50 company-currency
            }
        )
        pricelist = self.env["product.pricelist"].create(
            {"name": "Dashboard EUR Pricelist", "currency_id": foreign_currency.id}
        )
        partner = self.env["res.partner"].create({"name": "Dashboard EUR Customer"})
        product = self.env["product.product"].create(
            {"name": "Dashboard EUR Product", "list_price": 500.0}
        )
        order = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "pricelist_id": pricelist.id,
                "order_line": [
                    (0, 0, {"product_id": product.id, "product_uom_qty": 2})
                ],
            }
        )
        order.action_confirm()
        self.assertEqual(order.currency_id, foreign_currency)
        expected = foreign_currency._convert(
            order.amount_total,
            self.company.currency_id,
            self.company,
            fields.Date.context_today(self.env.user),
        )
        self.assertEqual(self._kpi()["sales_mtd_revenue"], expected)
        self.assertNotEqual(
            expected,
            order.amount_total,
            "the test must actually exercise a real conversion, not a 1:1 rate",
        )

    def test_mfg_avg_variance_pct(self):
        workcenter = self.env["mrp.workcenter"].create({"name": "Dashboard Workcenter"})
        component = self.env["product.product"].create(
            {"name": "Dashboard Raw Material", "is_storable": True}
        )
        finished = self.env["product.product"].create(
            {"name": "Dashboard Finished Good", "is_storable": True}
        )
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": finished.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [(0, 0, {"product_id": component.id, "product_qty": 1.0})],
                "operation_ids": [
                    (0, 0, {"name": "Assemble", "workcenter_id": workcenter.id}),
                ],
            }
        )
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.company.id)], limit=1
        )
        self.env["stock.quant"]._update_available_quantity(
            component, warehouse.lot_stock_id, 100.0
        )
        mo = self.env["mrp.production"].create(
            {
                "product_id": finished.id,
                "product_qty": 10.0,
                "bom_id": bom.id,
                "product_uom_id": finished.uom_id.id,
            }
        )
        mo.action_confirm()
        workorder = mo.workorder_ids
        workorder.write(
            {
                "qty_produced": 8.0,
                "state": "done",
                "date_finished": fields.Datetime.now(),
            }
        )
        self.assertEqual(self._kpi()["mfg_avg_variance_pct"], -20.0)

    def test_logistics_on_time_pct(self):
        vendor = self.env["res.partner"].create({"name": "Dashboard Vendor"})
        product = self.env["product.product"].create(
            {"name": "Dashboard Logistics Product", "is_storable": True}
        )
        po = self.env["purchase.order"].create(
            {
                "partner_id": vendor.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_qty": 5.0,
                            "price_unit": 10.0,
                        },
                    )
                ],
            }
        )
        po.button_confirm()
        po.order_line.date_planned = fields.Datetime.now() + timedelta(days=5)
        picking = po.picking_ids
        picking.move_ids.quantity = 5.0
        picking.move_ids.picked = True
        picking.button_validate()
        self.assertTrue(picking.bpro_on_time)
        self.assertEqual(self._kpi()["logistics_on_time_pct"], 100.0)

    def test_inventory_pending_adjustments(self):
        location = self.env["stock.location"].create(
            {"name": "Dashboard Test Bin", "usage": "internal"}
        )
        product = self.env["product.product"].create(
            {
                "name": "Dashboard Test Adjustment Product",
                "is_storable": True,
                "standard_price": 50.0,
            }
        )
        self.env["bpro.policy"].create(
            {
                "company_id": self.company.id,
                "key": "stock_adjustment_value",
                "numeric_value": 10.0,
            }
        )
        quant = self.env["stock.quant"].create(
            {
                "product_id": product.id,
                "location_id": location.id,
                "inventory_quantity": 1000.0,
                "bpro_adjustment_reason": "large recount",
            }
        )
        quant.action_apply_inventory()
        self.assertEqual(self._kpi()["inventory_pending_adjustments"], 1)

    def test_hr_pending_expense_approvals(self):
        self.env["account.chart.template"].try_loading(
            "generic_coa", self.company, install_demo=False
        )
        product = self.env["product.product"].create(
            {"name": "Dashboard Expense Product", "can_be_expensed": True}
        )
        employee = self.env["hr.employee"].create({"name": "Dashboard Expense Employee"})
        self.env["bpro.policy"].create(
            {
                "company_id": self.company.id,
                "key": "hr_expense_finance_approval_pct",
                "numeric_value": 100.0,
            }
        )
        sheet = self.env["hr.expense.sheet"].create(
            {
                "name": "Dashboard Test Expense",
                "employee_id": employee.id,
                "expense_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Big expense",
                            "employee_id": employee.id,
                            "product_id": product.id,
                            "total_amount": 1000.0,
                        },
                    )
                ],
            }
        )
        sheet.action_submit_sheet()
        self.assertEqual(self._kpi()["hr_pending_expense_approvals"], 1)

    def test_quality_pass_rate(self):
        point = self.env["bpro.quality.point"].create(
            {"name": "Dashboard QC Point", "operation": "incoming"}
        )
        product = self.env["product.product"].create(
            {"name": "Dashboard QC Product", "is_storable": True}
        )
        self.env["bpro.quality.check"].create(
            {
                "quality_point_id": point.id,
                "product_id": product.id,
                "company_id": self.company.id,
                "result": "pass",
            }
        )
        self.env["bpro.quality.check"].create(
            {
                "quality_point_id": point.id,
                "product_id": product.id,
                "company_id": self.company.id,
                "result": "fail",
            }
        )
        # a "to do" check must not count in either the numerator or
        # denominator - only decided checks form the pass rate
        self.env["bpro.quality.check"].create(
            {
                "quality_point_id": point.id,
                "product_id": product.id,
                "company_id": self.company.id,
            }
        )
        self.assertEqual(self._kpi()["quality_pass_rate_pct"], 50.0)

    def test_plant_asset_book_value(self):
        self.env["account.chart.template"].try_loading(
            "generic_coa", self.company, install_demo=False
        )
        expense_account = self.env["account.account"].search(
            [("account_type", "=", "expense")], limit=1
        )
        accumulated_account = self.env["account.account"].search(
            [("account_type", "=", "asset_non_current")], limit=1
        )
        asset = self.env["bpro.plant.asset"].create(
            {
                "name": "Dashboard Test Asset",
                "acquisition_date": "2026-01-01",
                "acquisition_cost": 12000.0,
                "useful_life_months": 12,
                "depreciation_expense_account_id": expense_account.id,
                "accumulated_depreciation_account_id": accumulated_account.id,
            }
        )
        asset.action_confirm()
        self.assertEqual(self._kpi()["plant_total_asset_book_value"], 12000.0)

    def test_project_pending_budget_approvals(self):
        self.env["bpro.policy"].create(
            {
                "company_id": self.company.id,
                "key": "project_budget_overrun_pct",
                "numeric_value": 10.0,
            }
        )
        project = self.env["project.project"].create(
            {
                "name": "Dashboard Test Project",
                "allow_timesheets": True,
                "company_id": self.company.id,
            }
        )
        task = self.env["project.task"].create(
            {
                "name": "Dashboard Test Task",
                "project_id": project.id,
                "company_id": self.company.id,
                "allocated_hours": 5.0,
            }
        )
        task_user = self.env["res.users"].create(
            {
                "name": "Dashboard Task User",
                "login": "dashboard-task-user@test.example",
                "email": "dashboard-task-user@test.example",
                "groups_id": [(4, self.env.ref("base.group_user").id)],
            }
        )
        employee = self.env["hr.employee"].create(
            {"name": "Dashboard Task Employee", "user_id": task_user.id}
        )
        self.env["account.analytic.line"].create(
            {
                "name": "overrun work",
                "project_id": project.id,
                "task_id": task.id,
                "employee_id": employee.id,
                "unit_amount": 20.0,
            }
        )
        self.assertEqual(
            task.approval_state,
            "pending",
            "logging hours far beyond allocated_hours must request approval",
        )
        self.assertEqual(self._kpi()["project_pending_budget_approvals"], 1)

    def test_fleet_trip_cost(self):
        brand = self.env["fleet.vehicle.model.brand"].create({"name": "Dashboard Brand"})
        model = self.env["fleet.vehicle.model"].create(
            {"name": "Dashboard Model", "brand_id": brand.id}
        )
        vehicle = self.env["fleet.vehicle"].create(
            {"model_id": model.id, "bpro_ownership_type": "owned"}
        )
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.company.id)], limit=1
        )
        product = self.env["product.product"].create(
            {"name": "Dashboard Fleet Product", "is_storable": True}
        )
        self.env["stock.quant"]._update_available_quantity(
            product, warehouse.lot_stock_id, 10.0
        )
        batch = self.env["stock.picking.batch"].create({"vehicle_id": vehicle.id})
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": warehouse.out_type_id.id,
                "location_id": warehouse.lot_stock_id.id,
                "location_dest_id": self.env.ref("stock.stock_location_customers").id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "name": product.name,
                            "product_id": product.id,
                            "product_uom_qty": 1.0,
                            "product_uom": product.uom_id.id,
                            "location_id": warehouse.lot_stock_id.id,
                            "location_dest_id": self.env.ref(
                                "stock.stock_location_customers"
                            ).id,
                        },
                    )
                ],
            }
        )
        batch.picking_ids = [(4, picking.id)]
        batch.bpro_trip_cost = 750.0
        batch.action_confirm()
        picking.action_assign()
        picking.move_ids.quantity = 1.0
        picking.move_ids.picked = True
        picking.button_validate()
        self.assertEqual(batch.state, "done")
        self.assertEqual(self._kpi()["fleet_trip_cost"], 750.0)
