from odoo import http
from odoo.http import request

from odoo.addons.website.controllers.main import Home


class MepPortalHome(Home):
    @http.route()
    def index(self, *args, **kw):
        # The ME Polymers gateway page replaces the website module's
        # editable homepage as the site root.
        return request.render("bpro_mep_portal.landing_page", {})
