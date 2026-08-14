from odoo import http
from odoo.http import request

from odoo.addons.website.controllers.main import Home


class HrmsPortalHome(Home):
    @http.route()
    def index(self, *args, **kw):
        # Serve the HRMS Suite Pro landing page as the site homepage
        # instead of the website module's editable homepage record.
        return request.render("bpro_hrms_portal.landing_page", {})
