import base64
import codecs
import re
import xml.etree.ElementTree as ET
from datetime import datetime

import defusedxml.ElementTree as SafeET

from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError

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
    # Real installations routinely rename/extend these once GST is enabled,
    # or use built-in Tally types this module didn't originally cover -
    # seen verbatim in a real client's export, alongside the generic names
    # above which some vouchers in the same file still used unchanged.
    "Stock Journal",
    "GST SALES",
    "GST Purchase",
    "Contra",
}
# Voucher types whose PARTYLEDGERNAME/ledger lines should resolve to a
# partner's payable (not receivable) account when the ledger name matches
# a partner - see _resolve_ledger. "GST Purchase" is this same relationship
# as "Purchase", just under the GST-specific voucher type name.
PAYABLE_PREFERRING_VOUCHER_TYPES = ("Purchase", "GST Purchase", "Payment", "Debit Note")
SALE_VOUCHER_TYPES = ("Sales", "GST SALES", "Credit Note")
PURCHASE_VOUCHER_TYPES = ("Purchase", "GST Purchase", "Debit Note")

# Confirmed-existing ledger names for the (direction, intra/inter-state, GST
# rate) combinations actually seen among this client's inventory lines whose
# GSTLEDGERSOURCE was blank (i.e. Tally sourced that line's GST
# classification from the stock item's own master, not a ledger override -
# see _ledger_entries). Deliberately only includes combinations verified
# against the real chart of accounts; anything else is left unresolved
# (falls through to "Unmapped ledger") rather than guessed, since a wrong
# Sales/Purchase ledger here would misstate real GST returns.
GST_RATE_FALLBACK_LEDGERS = {
    ("SALE", "LOCAL", "18"): "Kerala State 18% Sales",
    ("SALE", "INTERSTATE", "18"): "Interstate Gst Sales 18%",
    ("PURCHASE", "INTERSTATE", "18"): "Interstate Purchase 18%",
}
_RATE_NUMBER_RE = re.compile(r"(\d+(?:\.\d+)?)")


def parse_stock_item_gst_rates(raw_bytes):
    """Parses a Tally 'GST Rate Setup' export (GSTMASTERDISPNAME /
    GSTRATEIGSTRATE pairs) into {item_name: rate_string}, e.g. {"10mm Cork
    Black Sheet": "18"}. This is a separate, optional export from the Day
    Book - it only exists to fill in the GSTLEDGERSOURCE gap described on
    _ledger_entries, not to drive the main import."""
    text = sanitize_tally_xml_bytes(raw_bytes).decode("utf-8")
    pairs = re.findall(
        r"<GSTMASTERDISPNAME>(.*?)</GSTMASTERDISPNAME>\s*"
        r"<GSTRATEAPPLFROM>[^<]*</GSTRATEAPPLFROM>\s*"
        r"<GSTRATETAXTYPE>[^<]*</GSTRATETAXTYPE>\s*"
        r"<GSTRATEIGSTRATE>([^<]*)</GSTRATEIGSTRATE>",
        text,
    )
    rates = {}
    for name, rate in pairs:
        match = _RATE_NUMBER_RE.search(rate)
        if match:
            rates[name.strip()] = match.group(1)
    return rates


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
    gst_rate_filename = fields.Char()
    gst_rate_file = fields.Binary(
        help="Optional: Tally's 'GST Rate Setup' export (stock item name -> "
        "GST rate). Only used to resolve inventory lines whose GST "
        "classification came from the stock item's own master rather than "
        "a ledger override (see _ledger_entries) - leave blank if you don't "
        "have one; those lines will simply stay as Unmapped ledger "
        "exceptions instead."
    )
    state = fields.Selection(
        [("draft", "Draft"), ("done", "Done")], default="draft", readonly=True
    )
    imported_count = fields.Integer(readonly=True)
    exception_ids = fields.One2many(
        "bpro.tally.import.exception", "batch_id", readonly=True
    )
    move_ids = fields.One2many(
        "account.move", "bpro_tally_batch_id", readonly=True
    )

    def action_import(self):
        self.ensure_one()
        self.exception_ids.unlink()
        # action_import() is meant to be safely re-runnable (e.g. after
        # mapping more ledgers and wanting a fresh, complete pass) - without
        # this, every re-run would create a second, third, fourth... set of
        # journal entries for every voucher that already succeeded, since
        # nothing here previously checked for or removed a prior run's
        # postings. Reset to a clean slate first.
        old_moves = self.move_ids
        if old_moves:
            old_moves.button_draft()
            old_moves.unlink()
        try:
            clean_bytes = sanitize_tally_xml_bytes(base64.b64decode(self.xml_file))
            root = SafeET.fromstring(clean_bytes)
        except Exception as exc:
            raise UserError(_("Invalid XML file: %s") % exc)

        item_gst_rates = (
            parse_stock_item_gst_rates(base64.b64decode(self.gst_rate_file))
            if self.gst_rate_file
            else {}
        )

        journal = self._default_journal()
        imported = 0
        exception_vals = []
        for voucher_el in root.iter("VOUCHER"):
            error = self._import_one_voucher(voucher_el, journal, item_gst_rates)
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

    @staticmethod
    def _ledger_entries(voucher_el, voucher_type=None, item_gst_rates=None):
        """Yields (ledger_name, entry_element) pairs covering both Tally
        voucher XML layouts actually seen in this client's real export:

        - "voucher mode" (Payment/Receipt/Journal/Contra/Stock Journal):
          ALLLEDGERENTRIES.LIST, LEDGERNAME carries the ledger directly.
        - "invoice mode" (Sales/Purchase/GST SALES/GST Purchase/Credit
          Note/Debit Note): the party and any tax ledgers appear as
          LEDGERENTRIES.LIST, while each stock item's own ledger side
          appears in ALLINVENTORYENTRIES.LIST under GSTLEDGERSOURCE -
          invoice-mode entries carry no LEDGERNAME at all. Verified
          against real vouchers of every affected type: summing both
          lists' amounts (direction from ISDEEMEDPOSITIVE) balances to
          the paisa.

        GSTLEDGERSOURCE is only populated when Tally's GST
        classification for that line came from a ledger override
        (GSTSOURCETYPE="Ledger"); when it's sourced from the stock
        item's own master data instead (GSTSOURCETYPE="Stock Item" or
        "Company"), there is no ledger name in this export at all. If an
        item_gst_rates table was supplied (from a separate GST Rate Setup
        export), a fallback ledger name is derived from: the item's own
        GST rate (per-item, since one voucher can mix items at different
        rates - a voucher-level rate can't be assumed), whether this
        voucher's own tax lines show CGST+SGST (intra-state) or IGST
        (inter-state), and the voucher's Sale/Purchase direction. That
        candidate name still has to match a real existing account via the
        normal _resolve_ledger lookup below - if GST_RATE_FALLBACK_LEDGERS
        has no entry for this combination, or no matching account exists,
        it falls through to "Unmapped ledger" exactly as before, never a
        guessed posting.
        """
        entries = voucher_el.findall("ALLLEDGERENTRIES.LIST")
        if entries:
            for entry in entries:
                yield (entry.findtext("LEDGERNAME") or "").strip(), entry
            return
        ledger_entries = voucher_el.findall("LEDGERENTRIES.LIST")
        for entry in ledger_entries:
            yield (entry.findtext("LEDGERNAME") or "").strip(), entry

        tax_names = [(e.findtext("LEDGERNAME") or "").upper() for e in ledger_entries]
        has_igst = any("IGST" in n for n in tax_names)
        has_cgst_sgst = any("CGST" in n or "SGST" in n for n in tax_names)
        state = "INTERSTATE" if has_igst else ("LOCAL" if has_cgst_sgst else None)
        direction = (
            "SALE"
            if voucher_type in SALE_VOUCHER_TYPES
            else "PURCHASE" if voucher_type in PURCHASE_VOUCHER_TYPES else None
        )

        for entry in voucher_el.findall("ALLINVENTORYENTRIES.LIST"):
            name = (entry.findtext("GSTLEDGERSOURCE") or "").strip()
            if not name and item_gst_rates and state and direction:
                item = (entry.findtext("STOCKITEMNAME") or "").strip()
                rate = item_gst_rates.get(item)
                if rate:
                    name = GST_RATE_FALLBACK_LEDGERS.get((direction, state, rate), "")
            yield name, entry

    def _import_one_voucher(self, voucher_el, journal, item_gst_rates=None):
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
        for ledger_name, entry in self._ledger_entries(
            voucher_el, voucher_type, item_gst_rates
        ):
            account, partner = self._resolve_ledger(ledger_name, voucher_type)
            if not account:
                return self._exception(
                    voucher_number, _("Unmapped ledger: %s") % ledger_name
                )
            try:
                # ISDEEMEDPOSITIVE alone carries debit/credit direction, but
                # real-world exports (observed in this client's actual Day
                # Book) also sign AMOUNT itself for some voucher types (e.g.
                # Payment), giving a negative debit that can never balance
                # against its positive credit counterpart. Only the
                # magnitude is meaningful here.
                amount = abs(float(entry.findtext("AMOUNT") or "0"))
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
                        "partner_id": partner.id if partner else False,
                        "name": voucher_number,
                        "debit": amount if is_debit else 0.0,
                        "credit": 0.0 if is_debit else amount,
                    },
                )
            )

        if not line_vals:
            return self._exception(voucher_number, _("No ledger entries found"))

        # A real Tally export runs to thousands of vouchers, and not every
        # one of them is guaranteed to be well-formed from Odoo's side (a
        # rounding mismatch, an unbalanced entry, etc.) - create() itself
        # can raise just as easily as action_post() can. Both need to be
        # inside one savepoint: without it, a raised UserError leaves the
        # whole cursor's transaction aborted, and every subsequent voucher
        # in the loop would fail too, even the perfectly valid ones after
        # it, once the exception is caught in Python but the underlying
        # SQL transaction was never rolled back to a clean point.
        try:
            with self.env.cr.savepoint():
                move = self.env["account.move"].create(
                    {
                        "move_type": "entry",
                        "journal_id": journal.id,
                        "date": move_date,
                        "ref": voucher_number,
                        "line_ids": line_vals,
                        "bpro_tally_batch_id": self.id,
                    }
                )
                move.action_post()
        except (UserError, ValidationError) as exc:
            return self._exception(voucher_number, str(exc))
        return None

    def _resolve_ledger(self, ledger_name, voucher_type):
        """Returns (account, partner) - partner is the matched party when
        the ledger resolved via a partner's receivable/payable property,
        else None. Callers need both: the account to post to, and the
        partner to stamp on the line so per-customer/per-vendor reports
        (AR aging, partner statements) can actually attribute it - without
        this, every imported line would carry the right account balance
        but no partner_id at all, silently breaking those reports."""
        if not ledger_name:
            return None, None
        # Postgres's ILIKE (which "=ilike" compiles to) treats backslash as
        # its pattern escape character, so a ledger name containing a
        # literal backslash - seen in this client's real data, e.g. "Sadik
        # Meeran Current A\c" - silently fails to match its own exact
        # record otherwise. "%"/"_" are ILIKE wildcards for the same
        # reason. All three need escaping to make "=ilike" behave as the
        # plain case-insensitive exact match it's meant to be here.
        escaped_name = (
            ledger_name.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        partner = self.env["res.partner"].search(
            [("name", "=ilike", escaped_name)], limit=1
        )
        if partner:
            # party ledgers (the export side writes the partner's name as
            # LEDGERNAME for the receivable/payable line) resolve to that
            # partner's receivable or payable account, chosen by voucher
            # direction - not to a partner record directly, which isn't a
            # valid account.move.line.account_id.
            if voucher_type in PAYABLE_PREFERRING_VOUCHER_TYPES:
                account = (
                    partner.property_account_payable_id
                    or partner.property_account_receivable_id
                )
            else:
                account = (
                    partner.property_account_receivable_id
                    or partner.property_account_payable_id
                )
            return account, partner
        account = self.env["account.account"].search(
            [
                ("company_ids", "in", self.company_id.id),
                ("name", "=ilike", escaped_name),
            ],
            limit=1,
        )
        return account, None

    @staticmethod
    def _exception(voucher_number, reason):
        return {"voucher_number": voucher_number, "reason": reason}


class AccountMove(models.Model):
    _inherit = "account.move"

    bpro_tally_batch_id = fields.Many2one(
        "bpro.tally.import.batch",
        readonly=True,
        help="The Tally import batch that created this entry, so a re-run "
        "of that batch's import can find and replace it instead of "
        "posting a duplicate.",
    )


class BproTallyImportException(models.Model):
    _name = "bpro.tally.import.exception"
    _description = "Tally Import Exception"

    batch_id = fields.Many2one(
        "bpro.tally.import.batch", required=True, ondelete="cascade"
    )
    voucher_number = fields.Char()
    reason = fields.Char()
