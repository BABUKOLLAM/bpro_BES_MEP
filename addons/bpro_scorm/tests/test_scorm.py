import base64
import io
import zipfile

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase

MANIFEST = """<?xml version="1.0" encoding="UTF-8"?>
<manifest identifier="test" version="1.2"
    xmlns="http://www.imsproject.org/xsd/imscp_rootv1p1p2">
  <organizations default="ORG1">
    <organization identifier="ORG1">
      <item identifier="ITEM1" identifierref="RES1"><title>L1</title></item>
    </organization>
  </organizations>
  <resources>
    <resource identifier="RES1" type="webcontent" href="start.html">
      <file href="start.html"/>
    </resource>
  </resources>
</manifest>"""


def make_zip(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return base64.b64encode(buf.getvalue()).decode()


class TestScorm(TransactionCase):
    def test_launch_path_from_manifest(self):
        pkg = self.env["bpro.scorm.package"].create(
            {"name": "T1", "zip_file": make_zip(
                {"imsmanifest.xml": MANIFEST, "start.html": "<html/>"})}
        )
        self.assertEqual(pkg.launch_path, "start.html")
        self.assertEqual(pkg.player_url, f"/scorm/play/{pkg.id}")

    def test_index_html_fallback(self):
        pkg = self.env["bpro.scorm.package"].create(
            {"name": "T2", "zip_file": make_zip({"index.html": "<html/>"})}
        )
        self.assertEqual(pkg.launch_path, "index.html")

    def test_invalid_zip_rejected(self):
        with self.assertRaises(UserError):
            self.env["bpro.scorm.package"].create(
                {"name": "T3",
                 "zip_file": base64.b64encode(b"not a zip").decode()}
            )

    def test_no_launchable_content_rejected(self):
        with self.assertRaises(UserError):
            self.env["bpro.scorm.package"].create(
                {"name": "T4", "zip_file": make_zip({"readme.txt": "hi"})}
            )

    def test_path_traversal_in_zip_rejected(self):
        with self.assertRaises(UserError):
            self.env["bpro.scorm.package"].create(
                {"name": "T5", "zip_file": make_zip(
                    {"../../evil.sh": "rm -rf /", "index.html": "<html/>"})}
            )
