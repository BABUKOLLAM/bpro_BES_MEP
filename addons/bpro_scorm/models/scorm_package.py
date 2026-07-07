import base64
import io
import os
import shutil
import zipfile
from xml.etree import ElementTree

from odoo import api, fields, models
from odoo.exceptions import UserError

SCORM_ROOT = "/var/lib/odoo/bpro_scorm"


class ScormPackage(models.Model):
    _name = "bpro.scorm.package"
    _description = "SCORM Package"

    name = fields.Char(required=True)
    zip_file = fields.Binary(string="SCORM Zip (1.2)", attachment=True)
    zip_filename = fields.Char()
    launch_path = fields.Char(
        string="Launch File", readonly=True,
        help="Detected from imsmanifest.xml on upload.",
    )
    channel_id = fields.Many2one("slide.channel", string="Course")
    slide_id = fields.Many2one(
        "slide.slide",
        string="Completion Slide",
        domain="[('channel_id', '=', channel_id)]",
        help="Slide marked as completed when the SCORM content reports "
        "completed/passed. Add a slide of any type to the course to act "
        "as the SCORM lesson's placeholder.",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Owner Company",
        default=lambda self: self.env.company,
    )
    attempt_ids = fields.One2many("bpro.scorm.attempt", "package_id")
    attempt_count = fields.Integer(compute="_compute_attempt_count")
    player_url = fields.Char(compute="_compute_player_url")

    def _compute_attempt_count(self):
        for rec in self:
            rec.attempt_count = len(rec.attempt_ids)

    def _compute_player_url(self):
        for rec in self:
            rec.player_url = f"/scorm/play/{rec.id}" if rec.id else False

    def _extract_dir(self):
        self.ensure_one()
        return os.path.join(SCORM_ROOT, str(self.id))

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.filtered("zip_file")._extract_zip()
        return records

    def write(self, vals):
        res = super().write(vals)
        if vals.get("zip_file"):
            self._extract_zip()
        return res

    def unlink(self):
        for rec in self:
            shutil.rmtree(rec._extract_dir(), ignore_errors=True)
        return super().unlink()

    def _extract_zip(self):
        for rec in self:
            target = rec._extract_dir()
            shutil.rmtree(target, ignore_errors=True)
            os.makedirs(target, exist_ok=True)
            data = base64.b64decode(rec.zip_file)
            if len(data) > 300 * 1024 * 1024:
                raise UserError("SCORM package exceeds the 300 MB limit.")
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as zf:
                    for member in zf.namelist():
                        # prevent path traversal out of the target dir
                        dest = os.path.realpath(os.path.join(target, member))
                        if not dest.startswith(os.path.realpath(target) + os.sep):
                            raise UserError(f"Unsafe path in zip: {member}")
                    zf.extractall(target)
            except zipfile.BadZipFile:
                raise UserError("The uploaded file is not a valid zip archive.")
            rec.launch_path = rec._find_launch_path(target)

    def _find_launch_path(self, target):
        """Parse imsmanifest.xml for the default organization's first
        resource href. Fall back to index.html if no manifest."""
        manifest = os.path.join(target, "imsmanifest.xml")
        if not os.path.isfile(manifest):
            if os.path.isfile(os.path.join(target, "index.html")):
                return "index.html"
            raise UserError("No imsmanifest.xml or index.html found in the package.")
        try:
            tree = ElementTree.parse(manifest)
        except ElementTree.ParseError as e:
            raise UserError(f"Invalid imsmanifest.xml: {e}") from e
        root = tree.getroot()
        ns = {"": root.tag.split("}")[0].strip("{")} if "}" in root.tag else {}
        def findall(el, path):
            return el.findall(path, ns) if ns else el.findall(path)
        resources = {
            r.get("identifier"): r.get("href")
            for r in findall(root, ".//resources/resource")
            if r.get("href")
        }
        for item in findall(root, ".//organizations/organization/item"):
            href = resources.get(item.get("identifierref"))
            if href:
                return href
        if resources:
            return next(iter(resources.values()))
        raise UserError("No launchable resource found in imsmanifest.xml.")

    def action_open_player(self):
        self.ensure_one()
        return {"type": "ir.actions.act_url", "url": self.player_url, "target": "new"}


class ScormAttempt(models.Model):
    _name = "bpro.scorm.attempt"
    _description = "SCORM Attempt"
    _rec_name = "package_id"

    package_id = fields.Many2one(
        "bpro.scorm.package", required=True, ondelete="cascade"
    )
    user_id = fields.Many2one(
        "res.users", required=True, default=lambda self: self.env.user
    )
    lesson_status = fields.Char(default="not attempted")
    score_raw = fields.Char(string="Score")
    suspend_data = fields.Text()
    completed_on = fields.Datetime()

    _sql_constraints = [
        (
            "attempt_unique",
            "UNIQUE(package_id, user_id)",
            "One attempt record per user and package.",
        ),
    ]
