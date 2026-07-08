import base64
import xml.etree.ElementTree as ET
from datetime import datetime

import defusedxml.ElementTree as SafeET

from odoo import _, fields, models
from odoo.exceptions import UserError

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
            root = SafeET.fromstring(base64.b64decode(self.xml_file))
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
