import re

from odoo.tests.common import HttpCase, tagged


@tagged("-at_install", "post_install")
class TestTallyLargeUploadController(HttpCase):
    def _get_csrf_token(self, html):
        match = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
        self.assertTrue(match, "csrf token not found on upload page")
        return match.group(1)

    def test_upload_creates_import_batch_bypassing_json_rpc_limit(self):
        self.authenticate("admin", "admin")

        page = self.url_open("/bpro_finance/tally_import/upload")
        self.assertEqual(page.status_code, 200)
        csrf_token = self._get_csrf_token(page.text)

        xml_bytes = (
            b'<?xml version="1.0" encoding="UTF-8"?>'
            b"<ENVELOPE><HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>"
            b"<BODY><IMPORTDATA><REQUESTDESC><REPORTNAME>Vouchers</REPORTNAME></REQUESTDESC>"
            b"<REQUESTDATA></REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>"
        )
        response = self.url_open(
            "/bpro_finance/tally_import/upload",
            data={"csrf_token": csrf_token},
            files={"xml_file": ("upload_test.xml", xml_bytes, "text/xml")},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("model=bpro.tally.import.batch", response.url)

        batch = self.env["bpro.tally.import.batch"].search(
            [("xml_filename", "=", "upload_test.xml")]
        )
        self.assertTrue(batch, "upload did not create a bpro.tally.import.batch record")
        self.assertTrue(batch.xml_file)

    def test_upload_page_requires_login(self):
        # a fresh, unauthenticated session must be redirected to the login
        # page rather than reaching the upload form - auth='user' routes
        # redirect (not error), and the login page itself is a 200, so the
        # real assertion is on where we end up, not the status code.
        self.opener.cookies.clear()
        page = self.url_open("/bpro_finance/tally_import/upload")
        self.assertIn("/web/login", page.url)
