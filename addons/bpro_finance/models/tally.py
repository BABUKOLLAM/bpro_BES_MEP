import base64
import codecs
import re
import xml.etree.ElementTree as ET
from datetime import datetime

import defusedxml.ElementTree as SafeET

from odoo import _, fields, models
from odoo.exceptions import UserError

# XML 1.0 only permits #x9, #xA, #xD, #x20-#xD7FF, #xE000-#xFFFD,
# #x10000-#x10FFFF. Real Tally exports have been observed emitting stray
# control-character references (seen in practice: a literal U+0005 byte and
# a "&#4;" reference, both inside otherwise-unremarkable classification
# fields like VATDEALERTYPE) that violate this - not a corner case worth
# ignoring, since a single bad byte anywhere in a multi-hundred-MB export
# would otherwise reject the whole file. Strip anything illegal (as a
# literal char or as a decimal/hex numeric reference) before parsing.
_ILLEGAL_XML_CHARS_RE = re.compile(
    "[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f\ufdd0-\ufdef\ufffe\uffff]"
)
_NUMERIC_CHARREF_RE = re.compile(r"&#(x[0-9a-fA-F]+|[0-9]+);")


def _is_legal_xml_codepoint(cp):
    return (
        cp in (0x9, 0xA, 0xD)
        or 0x20 <= cp <= 0xD7FF
        or 0xE000 <= cp <= 0xFFFD
        or 0x10000 <= cp <= 0x10FFFF
    )


def _strip_illegal_charref(match):
    token = match.group(1)
    cp = int(token[1:], 16) if token.lower().startswith("x") else int(token)
    return "" if not _is_legal_xml_codepoint(cp) else match.group(0)


def sanitize_tally_xml_bytes(raw_bytes):
    """Decode a raw Tally export (routinely UTF-16, sometimes UTF-8) and
    strip characters/numeric references that are illegal per XML 1.0,
    returning clean UTF-8 bytes ready for a standard parser.

    Encoding is picked from the BOM, not a decode-and-hope try/except:
    'utf-16' will happily decode arbitrary UTF-8 bytes (any even-length
    byte string decodes without error, just as garbage) rather than
    raising, so a try/except would silently corrupt this module's own
    plain-UTF-8 exports instead of falling through to the UTF-8 branch.
    """
    if raw_bytes.startswith(codecs.BOM_UTF16_LE) or raw_bytes.startswith(codecs.BOM_UTF16_BE):
        text = raw_bytes.decode("utf-16")
    elif raw_bytes.startswith(codecs.BOM_UTF8):
        text = raw_bytes.decode("utf-8-sig")
    else:
        text = raw_bytes.decode("utf-8")
    text = _ILLEGAL_XML_CHARS_RE.sub("", text)
    text = _NUMERIC_CHARREF_RE.sub(_strip_illegal_charref, text)
    # the now-decoded text carries no meaningful original encoding anymore;
    # drop any encoding= attribute in the prolog so it doesn't claim to be
    # something other than the UTF-8 bytes we're about to emit.
    text = re.sub(r'encoding="[^"]*"', 'encoding="UTF-8"', text, count=1)
    return text.encode("utf-8")


VOUCHER_TYPE_MAP = {
    "out_invoice": "Sales",
    "in_invoice": "Purchase",
    "out_refund": "Credit Note",
    "in_refund": "Debit Note",
}
KNOWN_VOUCHER_TYPES = {
    "Sales",
    "Purchase",
    "Receipt",
    "Payment",
    "Journal",
    "Credit Note",
    "Debit Note",
}


class BproTallyExportBatch(models.Model):
    _name = "bpro.tally.export.batch"
    _description = "Tally XML Export Batch"
    _order = "create_date desc"

    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, required=True
    )
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    state = fields.Selection(
        [("draft", "Draft"), ("done", "Done")], default="draft", readonly=True
    )
    voucher_count = fields.Integer(readonly=True)
    xml_filename = fields.Char(readonly=True)
    xml_file = fields.Binary(readonly=True, attachment=True)

    def action_export(self):
        self.ensure_one()
        moves = self.env["account.move"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("state", "=", "posted"),
                ("date", ">=", self.date_from),
                ("date", "<=", self.date_to),
            ]
        )
        xml_bytes = self._build_tally_xml(moves)
        self.write(
            {
                "state": "done",
                "voucher_count": len(moves),
                "xml_filename": "tally_export_%s_%s.xml" % (self.date_from, self.date_to),
                "xml_file": base64.b64encode(xml_bytes),
            }
        )
        return True

    def _voucher_type_for_move(self, move):
        if move.move_type in VOUCHER_TYPE_MAP:
            return VOUCHER_TYPE_MAP[move.move_type]
        if move.move_type == "entry" and move.origin_payment_id:
            return (
                "Receipt"
                if move.origin_payment_id.payment_type == "inbound"
                else "Payment"
            )
        return "Journal"

    def _build_tally_xml(self, moves):
        """Builds the real Tally ENVELOPE/HEADER/BODY/IMPORTDATA/
        REQUESTDATA/TALLYMESSAGE/VOUCHER schema. Simplification, documented
        rather than silently assumed: ledger AMOUNT is always emitted
        positive, with ISDEEMEDPOSITIVE (Yes=debit/No=credit) carrying the
        direction - real Tally exports sometimes sign the amount itself by
        direction too, and that convention varies by version/report, which
        is exactly the kind of Tally-version-specific nuance this project
        explicitly deferred (see Volume 4 assumptions). This is internally
        consistent and round-trips correctly with this module's own
        import - it is not asserted to byte-for-byte match every real
        Tally installation's export.
        """
        envelope = ET.Element("ENVELOPE")
        header = ET.SubElement(envelope, "HEADER")
        ET.SubElement(header, "TALLYREQUEST").text = "Import Data"
        body = ET.SubElement(envelope, "BODY")
        import_data = ET.SubElement(body, "IMPORTDATA")
        request_desc = ET.SubElement(import_data, "REQUESTDESC")
        ET.SubElement(request_desc, "REPORTNAME").text = "Vouchers"
        request_data = ET.SubElement(import_data, "REQUESTDATA")

        for move in moves:
            tally_message = ET.SubElement(request_data, "TALLYMESSAGE")
            voucher_type = self._voucher_type_for_move(move)
            voucher = ET.SubElement(
                tally_message, "VOUCHER", VCHTYPE=voucher_type, ACTION="Create"
            )
            ET.SubElement(voucher, "DATE").text = move.date.strftime("%Y%m%d")
            ET.SubElement(voucher, "VOUCHERTYPENAME").text = voucher_type
            ET.SubElement(voucher, "VOUCHERNUMBER").text = move.name or ""
            if move.partner_id:
                ET.SubElement(voucher, "PARTYLEDGERNAME").text = move.partner_id.name

            for line in move.line_ids:
                entry = ET.SubElement(voucher, "ALLLEDGERENTRIES.LIST")
                ledger_name = (
                    line.partner_id.name if line.partner_id else line.account_id.name
                )
                ET.SubElement(entry, "LEDGERNAME").text = ledger_name
                is_debit = line.debit > 0
                ET.SubElement(entry, "ISDEEMEDPOSITIVE").text = (
                    "Yes" if is_debit else "No"
                )
                amount = line.debit if is_debit else line.credit
                ET.SubElement(entry, "AMOUNT").text = "%.2f" % amount

        return ET.tostring(envelope, encoding="utf-8", xml_declaration=True)


class BproTallyImportBatch(models.Model):
    _name = "bpro.tally.import.batch"
    _description = "Tally XML Import Batch"
    _order = "create_date desc"

    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, required=True
    )
    xml_filename = fields.Char()
    xml_file = fields.Binary(required=True)
    state = fields.Selection(
        [("draft", "Draft"), ("done", "Done")], default="draft", readonly=True
    )
    imported_count = fields.Integer(readonly=True)
    exception_ids = fields.One2many(
        "bpro.tally.import.exception", "batch_id", readonly=True
    )

    def action_import(self):
        self.ensure_one()
        self.exception_ids.unlink()
        try:
            clean_bytes = sanitize_tally_xml_bytes(base64.b64decode(self.xml_file))
            root = SafeET.fromstring(clean_bytes)
        except Exception as exc:
            raise UserError(_("Invalid XML file: %s") % exc)

        journal = self._default_journal()
        imported = 0
        exception_vals = []
        for voucher_el in root.iter("VOUCHER"):
            error = self._import_one_voucher(voucher_el, journal)
            if error:
                exception_vals.append(error)
            else:
                imported += 1

        self.exception_ids = [(0, 0, vals) for vals in exception_vals]
        self.write({"state": "done", "imported_count": imported})
        return True

    def _default_journal(self):
        journal = self.env["account.journal"].search(
            [("company_id", "=", self.company_id.id), ("type", "=", "general")],
            limit=1,
        )
        if not journal:
            raise UserError(
                _("No Miscellaneous Operations journal found for %s.")
                % self.company_id.name
            )
        return journal

    def _import_one_voucher(self, voucher_el, journal):
        """Returns a dict of bpro.tally.import.exception vals if the
        voucher couldn't be imported, or None if it was posted."""
        voucher_number = voucher_el.findtext("VOUCHERNUMBER") or ""
        voucher_type = voucher_el.findtext("VOUCHERTYPENAME") or voucher_el.get(
            "VCHTYPE"
        )
        if voucher_type not in KNOWN_VOUCHER_TYPES:
            return self._exception(
                voucher_number, _("Unknown voucher type: %s") % voucher_type
            )

        date_str = voucher_el.findtext("DATE")
        try:
            move_date = datetime.strptime(date_str, "%Y%m%d").date()
        except (TypeError, ValueError):
            return self._exception(voucher_number, _("Invalid or missing date"))

        line_vals = []
        for entry in voucher_el.findall("ALLLEDGERENTRIES.LIST"):
            ledger_name = (entry.findtext("LEDGERNAME") or "").strip()
            account = self._resolve_ledger(ledger_name, voucher_type)
            if not account:
                return self._exception(
                    voucher_number, _("Unmapped ledger: %s") % ledger_name
                )
            try:
                amount = float(entry.findtext("AMOUNT") or "0")
            except ValueError:
                return self._exception(
                    voucher_number, _("Invalid amount for ledger %s") % ledger_name
                )
            is_debit = (entry.findtext("ISDEEMEDPOSITIVE") or "").strip().lower() == "yes"
            line_vals.append(
                (
                    0,
                    0,
                    {
                        "account_id": account.id,
                        "name": voucher_number,
                        "debit": amount if is_debit else 0.0,
                        "credit": 0.0 if is_debit else amount,
                    },
                )
            )

        if not line_vals:
            return self._exception(voucher_number, _("No ledger entries found"))

        move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "journal_id": journal.id,
                "date": move_date,
                "ref": voucher_number,
                "line_ids": line_vals,
            }
        )
        try:
            move.action_post()
        except UserError as exc:
            move.unlink()
            return self._exception(voucher_number, str(exc))
        return None

    def _resolve_ledger(self, ledger_name, voucher_type):
        if not ledger_name:
            return None
        partner = self.env["res.partner"].search(
            [("name", "=ilike", ledger_name)], limit=1
        )
        if partner:
            # party ledgers (the export side writes the partner's name as
            # LEDGERNAME for the receivable/payable line) resolve to that
            # partner's receivable or payable account, chosen by voucher
            # direction - not to a partner record directly, which isn't a
            # valid account.move.line.account_id.
            if voucher_type in ("Purchase", "Payment", "Debit Note"):
                return (
                    partner.property_account_payable_id
                    or partner.property_account_receivable_id
                )
            return (
                partner.property_account_receivable_id
                or partner.property_account_payable_id
            )
        return self.env["account.account"].search(
            [
                ("company_ids", "in", self.company_id.id),
                ("name", "=ilike", ledger_name),
            ],
            limit=1,
        )

    @staticmethod
    def _exception(voucher_number, reason):
        return {"voucher_number": voucher_number, "reason": reason}


class BproTallyImportException(models.Model):
    _name = "bpro.tally.import.exception"
    _description = "Tally Import Exception"

    batch_id = fields.Many2one(
        "bpro.tally.import.batch", required=True, ondelete="cascade"
    )
    voucher_number = fields.Char()
    reason = fields.Char()
