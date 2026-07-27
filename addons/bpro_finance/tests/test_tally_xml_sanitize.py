from odoo.tests.common import TransactionCase

from ..models.tally import sanitize_tally_xml_bytes
from .common import FinanceTestCommon

# Reproduces a real fault found in a client's actual Tally export (a
# ~330MB Day Book XML): UTF-16 encoded, with a literal U+0005 control byte
# and a "&#4;" numeric reference both embedded inside an otherwise-normal
# classification field. Both are illegal per XML 1.0 - a strict parser is
# *right* to reject them - so the fix is sanitizing before parsing, not
# loosening the parser.
UTF16_VOUCHER_WITH_ILLEGAL_CHARS = (
    "<?xml version=\"1.0\" encoding=\"UTF-16\"?>\n"
    "<ENVELOPE><HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>"
    "<BODY><IMPORTDATA><REQUESTDESC><REPORTNAME>Vouchers</REPORTNAME></REQUESTDESC>"
    "<REQUESTDATA><TALLYMESSAGE>"
    "<VOUCHER VCHTYPE=\"Journal\" ACTION=\"Create\">"
    "<DATE>20260615</DATE><VOUCHERTYPENAME>Journal</VOUCHERTYPENAME>"
    "<VOUCHERNUMBER>TALLY-SANITIZE-001</VOUCHERNUMBER>"
    "<VATDEALERTYPE>\x05&#4; Unknown</VATDEALERTYPE>"
    "<ALLLEDGERENTRIES.LIST><LEDGERNAME>{cash}</LEDGERNAME>"
    "<ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE><AMOUNT>750.00</AMOUNT>"
    "</ALLLEDGERENTRIES.LIST>"
    "<ALLLEDGERENTRIES.LIST><LEDGERNAME>{income}</LEDGERNAME>"
    "<ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE><AMOUNT>750.00</AMOUNT>"
    "</ALLLEDGERENTRIES.LIST>"
    "</VOUCHER>"
    "</TALLYMESSAGE></REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>"
)


class TestSanitizeTallyXmlUnit(TransactionCase):
    def test_strips_literal_control_char_and_illegal_numeric_ref(self):
        raw = "<a>\x05text&#4;more&#9;tab&#65;A</a>".encode("utf-16")
        clean = sanitize_tally_xml_bytes(raw).decode("utf-8")
        self.assertNotIn("\x05", clean)
        self.assertNotIn("&#4;", clean)
        # legal references/chars must survive: tab (#9) and 'A' (#65)
        self.assertIn("&#9;", clean)
        self.assertIn("&#65;", clean)
        self.assertIn("text", clean)
        self.assertIn("more", clean)


class TestTallyImportSanitizesRealWorldExport(FinanceTestCommon):
    def test_utf16_export_with_illegal_chars_still_imports(self):
        cash = self.env["account.account"].search(
            [("company_ids", "in", self.company.id), ("account_type", "=", "asset_cash")],
            limit=1,
        )
        income = self.env["account.account"].search(
            [("company_ids", "in", self.company.id), ("account_type", "=", "income")],
            limit=1,
        )
        self.assertTrue(cash and income, "test CoA must have cash/income accounts")

        xml_text = UTF16_VOUCHER_WITH_ILLEGAL_CHARS.format(
            cash=cash.name, income=income.name
        )
        import base64

        import_batch = self.env["bpro.tally.import.batch"].create(
            {
                "xml_file": base64.b64encode(xml_text.encode("utf-16")),
                "xml_filename": "utf16_with_illegal_chars.xml",
            }
        )
        import_batch.action_import()

        self.assertEqual(import_batch.state, "done")
        self.assertFalse(
            import_batch.exception_ids,
            "a stray illegal control char must not block an otherwise valid voucher",
        )
        self.assertEqual(import_batch.imported_count, 1)
