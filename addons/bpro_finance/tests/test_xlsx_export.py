import base64
from datetime import date
from unittest import mock

from odoo.exceptions import UserError

from .common import FinanceTestCommon


class TestXlsxExport(FinanceTestCommon):
    """Exercises the shared bpro_xlsx_export mixin through the Trial
    Balance wizard (any report would do - the mixin logic is generic);
    a couple of other reports get a lighter smoke test to confirm the
    wiring, not the mixin behaviour itself."""

    def setUp(self):
        super().setUp()
        move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": "2026-04-05",
                "line_ids": [
                    (0, 0, {
                        "account_id": self.env["account.account"].search(
                            [("account_type", "=", "asset_cash"), ("company_ids", "in", self.company.id)],
                            limit=1,
                        ).id,
                        "debit": 500.0, "credit": 0.0,
                    }),
                    (0, 0, {
                        "account_id": self.env["account.account"].search(
                            [("account_type", "=", "income"), ("company_ids", "in", self.company.id)],
                            limit=1,
                        ).id,
                        "debit": 0.0, "credit": 500.0,
                    }),
                ],
            }
        )
        move.action_post()

    def _generated_trial_balance(self):
        wizard = self.env["bpro.trial.balance.wizard"].create(
            {"date_from": date(2026, 4, 1), "date_to": date(2026, 4, 30)}
        )
        wizard.action_generate()
        self.assertTrue(wizard.line_ids, "fixture must produce at least one line")
        return wizard

    def test_export_without_generating_raises(self):
        wizard = self.env["bpro.trial.balance.wizard"].create(
            {"date_from": date(2026, 4, 1), "date_to": date(2026, 4, 30)}
        )
        with self.assertRaises(UserError):
            wizard.action_export_xlsx()

    def test_default_columns_are_all_registered_columns_for_the_report(self):
        wizard = self._generated_trial_balance()
        available = self.env["bpro.report.column"].search(
            [("report_model", "=", "bpro.trial.balance.wizard")]
        )
        self.assertTrue(available)
        self.assertEqual(set(wizard.xlsx_column_ids.ids), set(available.ids))

    def test_export_produces_a_valid_xlsx_file(self):
        wizard = self._generated_trial_balance()
        action = wizard.action_export_xlsx()
        self.assertEqual(action["type"], "ir.actions.act_url")
        self.assertTrue(wizard.xlsx_file)
        self.assertTrue(wizard.xlsx_filename.endswith(".xlsx"))
        raw = base64.b64decode(wizard.xlsx_file)
        # .xlsx is a zip archive - "PK\x03\x04" is the local-file-header
        # magic bytes every valid zip (and therefore every valid xlsx)
        # starts with.
        self.assertEqual(raw[:4], b"PK\x03\x04")

    def test_export_with_a_column_subset_still_produces_a_valid_file(self):
        wizard = self._generated_trial_balance()
        only_account = self.env["bpro.report.column"].search(
            [("report_model", "=", "bpro.trial.balance.wizard"), ("technical_name", "=", "account_id")]
        )
        wizard.xlsx_column_ids = [(6, 0, only_account.ids)]
        wizard.action_export_xlsx()
        raw = base64.b64decode(wizard.xlsx_file)
        self.assertEqual(raw[:4], b"PK\x03\x04")

    def test_export_rejects_a_column_not_in_the_report_s_allowed_fields(self):
        wizard = self._generated_trial_balance()
        rogue = self.env["bpro.report.column"].create(
            {
                "report_model": "bpro.trial.balance.wizard",
                "technical_name": "create_uid",  # real field, but not whitelisted
                "name": "Not Allowed",
            }
        )
        wizard.xlsx_column_ids = [(6, 0, rogue.ids)]
        with self.assertRaises(UserError):
            wizard.action_export_xlsx()

    def test_export_rejects_a_field_that_does_not_exist_on_the_line_model(self):
        wizard = self._generated_trial_balance()
        column = self.env["bpro.report.column"].search(
            [("report_model", "=", "bpro.trial.balance.wizard"), ("technical_name", "=", "account_id")]
        )
        wizard.xlsx_column_ids = [(6, 0, column.ids)]
        Wizard = type(wizard)
        with mock.patch.object(Wizard, "_xlsx_export_fields", ["account_id", "not_a_real_field"]):
            with self.assertRaises(UserError):
                wizard.action_export_xlsx()

    def test_balance_sheet_export(self):
        wizard = self.env["bpro.balance.sheet.wizard"].create({"date_to": date(2026, 4, 30)})
        wizard.action_generate()
        wizard.action_export_xlsx()
        self.assertTrue(wizard.xlsx_file)

    def test_sales_margin_export(self):
        wizard = self.env["bpro.sales.margin.wizard"].create(
            {"date_from": date(2026, 4, 1), "date_to": date(2026, 4, 30)}
        )
        order = self.env["sale.order"].create(
            {
                "partner_id": self.customer.id,
                "date_order": "2026-04-10 10:00:00",
                "order_line": [
                    (0, 0, {"product_id": self.product.id, "product_uom_qty": 2, "price_unit": 100.0})
                ],
            }
        )
        order.action_confirm()
        order.write({"date_order": "2026-04-10 10:00:00"})
        wizard.action_generate()
        self.assertTrue(wizard.line_ids)
        wizard.action_export_xlsx()
        self.assertTrue(wizard.xlsx_file)

    def test_ar_aging_export(self):
        self._post_customer_invoice(750.0, "2026-04-01")
        wizard = self.env["bpro.ar.aging.wizard"].create({"as_of_date": date(2026, 4, 30)})
        wizard.action_generate()
        self.assertTrue(wizard.line_ids)
        wizard.action_export_xlsx()
        self.assertTrue(wizard.xlsx_file)
