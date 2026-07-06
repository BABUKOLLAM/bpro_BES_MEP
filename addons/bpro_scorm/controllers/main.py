import json
import mimetypes
import os

from markupsafe import Markup

from odoo import fields, http
from odoo.http import request

from ..models.scorm_package import SCORM_ROOT


class ScormController(http.Controller):
    def _get_package(self, package_id):
        package = request.env["bpro.scorm.package"].sudo().browse(package_id)
        if not package.exists() or not package.launch_path:
            return None
        return package

    @http.route("/scorm/play/<int:package_id>", type="http", auth="user")
    def scorm_play(self, package_id):
        package = self._get_package(package_id)
        if not package:
            return request.not_found()
        attempt = self._get_attempt(package)
        return request.render(
            "bpro_scorm.player",
            {
                "package": package,
                "content_url": f"/scorm/content/{package.id}/{package.launch_path}",
                "suspend_data_json": Markup(json.dumps(attempt.suspend_data or "")),
                "lesson_status_json": Markup(
                    json.dumps(attempt.lesson_status or "not attempted")
                ),
            },
        )

    @http.route(
        "/scorm/content/<int:package_id>/<path:subpath>", type="http", auth="user"
    )
    def scorm_content(self, package_id, subpath):
        package = self._get_package(package_id)
        if not package:
            return request.not_found()
        base = os.path.realpath(os.path.join(SCORM_ROOT, str(package.id)))
        full = os.path.realpath(os.path.join(base, subpath))
        if not full.startswith(base + os.sep) or not os.path.isfile(full):
            return request.not_found()
        mimetype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        with open(full, "rb") as f:
            return request.make_response(
                f.read(), [("Content-Type", mimetype)]
            )

    def _get_attempt(self, package):
        Attempt = request.env["bpro.scorm.attempt"].sudo()
        attempt = Attempt.search(
            [
                ("package_id", "=", package.id),
                ("user_id", "=", request.env.user.id),
            ],
            limit=1,
        )
        return attempt or Attempt.create(
            {"package_id": package.id, "user_id": request.env.user.id}
        )

    @http.route("/scorm/commit/<int:package_id>", type="json", auth="user")
    def scorm_commit(self, package_id, lesson_status=None, score_raw=None,
                     suspend_data=None):
        package = self._get_package(package_id)
        if not package:
            return {"error": "package not found"}
        attempt = self._get_attempt(package)
        vals = {}
        if lesson_status:
            vals["lesson_status"] = lesson_status
        if score_raw is not None:
            vals["score_raw"] = str(score_raw)
        if suspend_data is not None:
            vals["suspend_data"] = suspend_data
        completed = lesson_status in ("completed", "passed")
        if completed and not attempt.completed_on:
            vals["completed_on"] = fields.Datetime.now()
        if vals:
            attempt.write(vals)
        if completed and package.slide_id:
            self._mark_slide_completed(package.slide_id, request.env.user.partner_id)
        return {"ok": True, "completed": completed}

    def _mark_slide_completed(self, slide, partner):
        """Sudo mirror of slide._action_mark_completed for the given
        partner: the learner's backend rights don't cover slide models,
        but the attempt is theirs (auth='user' + own attempt row)."""
        slide = slide.sudo()
        channel = slide.channel_id
        if partner not in channel.channel_partner_ids.partner_id:
            channel._action_add_members(partner)
        SlidePartner = slide.env["slide.slide.partner"]
        existing = SlidePartner.search(
            [("slide_id", "=", slide.id), ("partner_id", "=", partner.id)]
        )
        if existing:
            existing.write({"completed": True})
        else:
            SlidePartner.create(
                {
                    "slide_id": slide.id,
                    "channel_id": channel.id,
                    "partner_id": partner.id,
                    "completed": True,
                    "vote": 0,
                }
            )
