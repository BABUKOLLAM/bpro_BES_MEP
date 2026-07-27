import base64

from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request

# Odoo's generic /web/dataset/call_kw JSON-RPC endpoint (used by the standard
# Binary widget) enforces a hard-coded 128MiB request body limit
# (odoo.http.DEFAULT_MAX_CONTENT_LENGTH), and JSON/base64 encoding inflates
# the payload further on top of that. Large real-world Tally exports
# (a full ledger history, not a single reconciliation batch) can exceed
# that. This route accepts the file as a plain multipart upload instead,
# with its own higher ceiling, so it never touches the JSON-RPC path.
MAX_TALLY_UPLOAD_BYTES = 1024 * 1024 * 1024  # 1 GiB


class BproTallyUploadController(http.Controller):
    @http.route(
        "/bpro_finance/tally_import/upload",
        type="http",
        auth="user",
        website=False,
        methods=["GET"],
    )
    def tally_upload_form(self, **kwargs):
        try:
            request.env["bpro.tally.import.batch"].check_access("create")
        except AccessError:
            return request.render("http_routing.404")
        return request.render("bpro_finance.tally_large_upload_page", {})

    @http.route(
        "/bpro_finance/tally_import/upload",
        type="http",
        auth="user",
        website=False,
        methods=["POST"],
        max_content_length=MAX_TALLY_UPLOAD_BYTES,
        csrf=True,
    )
    def tally_upload_submit(self, xml_file=None, **kwargs):
        Batch = request.env["bpro.tally.import.batch"]
        try:
            Batch.check_access("create")
        except AccessError:
            return request.render("http_routing.404")

        if not xml_file or not xml_file.filename:
            return request.render(
                "bpro_finance.tally_large_upload_page",
                {"error": "Please choose a file before uploading."},
            )

        content = xml_file.read()
        batch = Batch.create(
            {
                "xml_filename": xml_file.filename,
                "xml_file": base64.b64encode(content),
            }
        )
        return request.redirect(
            f"/web#model=bpro.tally.import.batch&view_type=form&id={batch.id}"
        )
