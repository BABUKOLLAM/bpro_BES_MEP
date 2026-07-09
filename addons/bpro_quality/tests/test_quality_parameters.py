from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestQualityParameters(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env["res.partner"].create({"name": "QC Test Vendor"})
        cls.product = cls.env["product.product"].create(
            {"name": "QC Test Sheet", "is_storable": True}
        )
        cls.point = cls.env["bpro.quality.point"].create(
            {
                "name": "Sheet Thickness Check",
                "operation": "incoming",
                "product_tmpl_id": cls.product.product_tmpl_id.id,
            }
        )
        cls.parameter = cls.env["bpro.quality.test.parameter"].create(
            {
                "name": "Thickness",
                "quality_point_id": cls.point.id,
                "uom_name": "mm",
                "min_value": 4.0,
                "max_value": 6.0,
                "target_value": 5.0,
            }
        )

    def _received_picking(self):
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "order_line": [
                    (0, 0, {"product_id": self.product.id, "product_qty": 5.0, "price_unit": 10.0})
                ],
            }
        )
        po.button_confirm()
        picking = po.picking_ids
        picking.move_ids.quantity = 5.0
        picking.move_ids.picked = True
        return picking

    def test_check_auto_creates_one_line_per_test_parameter(self):
        picking = self._received_picking()
        check = picking.bpro_quality_check_ids
        self.assertEqual(len(check.line_ids), 1)
        self.assertEqual(check.line_ids.parameter_id, self.parameter)

    def test_line_is_within_spec_computed_from_measured_value(self):
        picking = self._received_picking()
        line = picking.bpro_quality_check_ids.line_ids
        line.measured_value = 5.2
        self.assertTrue(line.is_within_spec)
        line.measured_value = 7.0
        self.assertFalse(line.is_within_spec)

    def test_cannot_pass_a_check_with_an_out_of_spec_measurement(self):
        picking = self._received_picking()
        check = picking.bpro_quality_check_ids
        check.line_ids.measured_value = 7.0
        with self.assertRaises(UserError):
            check.action_bpro_pass()

    def test_can_pass_a_check_with_all_measurements_within_spec(self):
        picking = self._received_picking()
        check = picking.bpro_quality_check_ids
        check.line_ids.measured_value = 5.0
        check.action_bpro_pass()
        self.assertEqual(check.result, "pass")

    def test_failing_a_check_creates_a_nonconformance(self):
        picking = self._received_picking()
        check = picking.bpro_quality_check_ids
        check.action_bpro_fail()
        self.assertEqual(len(check.nonconformance_ids), 1)
        self.assertEqual(check.nonconformance_ids.state, "open")
        self.assertEqual(check.nonconformance_ids.product_id, self.product)

    def test_failing_a_check_twice_does_not_duplicate_the_nonconformance(self):
        picking = self._received_picking()
        check = picking.bpro_quality_check_ids
        check.action_bpro_fail()
        check.action_bpro_fail()
        self.assertEqual(len(check.nonconformance_ids), 1)

    def test_print_coa_returns_the_report_action(self):
        picking = self._received_picking()
        check = picking.bpro_quality_check_ids
        check.line_ids.measured_value = 5.0
        check.action_bpro_pass()
        action = check.action_print_coa()
        self.assertEqual(action["report_name"], "bpro_quality.report_bpro_quality_coa_document")

    def test_checkpoint_without_test_parameters_still_works_as_simple_pass_fail(self):
        simple_product = self.env["product.product"].create(
            {"name": "QC Test Simple Product", "is_storable": True}
        )
        self.env["bpro.quality.point"].create(
            {
                "name": "Simple Visual Check",
                "operation": "incoming",
                "product_tmpl_id": simple_product.product_tmpl_id.id,
            }
        )
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "order_line": [
                    (0, 0, {"product_id": simple_product.id, "product_qty": 5.0, "price_unit": 10.0})
                ],
            }
        )
        po.button_confirm()
        picking = po.picking_ids
        picking.move_ids.quantity = 5.0
        picking.move_ids.picked = True
        check = picking.bpro_quality_check_ids
        self.assertFalse(check.line_ids)
        check.action_bpro_pass()
        self.assertEqual(check.result, "pass")
