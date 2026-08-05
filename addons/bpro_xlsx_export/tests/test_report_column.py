from odoo.tests.common import TransactionCase


class TestReportColumn(TransactionCase):
    def test_columns_filter_by_report_model(self):
        Column = self.env["bpro.report.column"]
        a = Column.create(
            {"report_model": "x.fake.report.a", "technical_name": "foo", "name": "Foo"}
        )
        Column.create(
            {"report_model": "x.fake.report.b", "technical_name": "bar", "name": "Bar"}
        )
        found = Column.search([("report_model", "=", "x.fake.report.a")])
        self.assertEqual(found, a)

    def test_default_order_is_report_model_then_sequence(self):
        Column = self.env["bpro.report.column"]
        Column.create(
            {"report_model": "x.fake.report.c", "technical_name": "second",
             "name": "Second", "sequence": 20}
        )
        Column.create(
            {"report_model": "x.fake.report.c", "technical_name": "first",
             "name": "First", "sequence": 10}
        )
        found = Column.search([("report_model", "=", "x.fake.report.c")])
        self.assertEqual(found.mapped("technical_name"), ["first", "second"])
