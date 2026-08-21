from odoo import models
from odoo.exceptions import UserError


class BaseImportGate(models.TransientModel):
    _inherit = "base_import.import"

    def execute_import(self, fields, columns, options, dryrun=False):
        """Route ordinary users' bulk imports through manager approval.

        Test runs (dryrun) stay open to everyone so uploaders can validate
        their file before submitting it. The real import is allowed for
        Direct Import users (admins/managers granted the group) and for
        the approval workflow itself (context flag set by
        bpro.data.upload.action_approve, which has already enforced the
        manager check).
        """
        if (
            not dryrun
            and not self.env.context.get("bpro_upload_approved")
            and not self.env.user.has_group("bpro_data_tools.group_direct_import")
        ):
            raise UserError(
                "Direct import is reserved for managers. Use the Test button "
                "here to validate your file, then submit it via the Data "
                "Uploads app - your manager approves it and the data is "
                "imported automatically."
            )
        return super().execute_import(fields, columns, options, dryrun=dryrun)
