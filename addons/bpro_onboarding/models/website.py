from odoo import models

# Menu URLs kept on a fresh client portal. Everything else from Odoo's
# website starter kit (Services, Pricing, About Us, Jobs, News, ...) is
# marketing placeholder content this backend HR/LMS platform doesn't need.
KEEP_MENU_URLS = {"/", "/slides"}


class Website(models.Model):
    _inherit = "website"

    def _bpro_strip_starter_content(self):
        """Send visitors straight to login instead of Odoo's generic
        'Your Company' starter homepage, and drop the placeholder
        marketing pages/menu items that come with the website module."""
        for site in self:
            site.homepage_url = "/web/login"
            pages = self.env["website.page"].sudo().search(
                [("website_id", "=", site.id), ("url", "not in", ["/"])]
            )
            pages.write({"is_published": False})
            menus = self.env["website.menu"].sudo().search(
                [
                    ("website_id", "=", site.id),
                    ("url", "not in", list(KEEP_MENU_URLS)),
                    ("parent_id", "!=", False),
                ]
            )
            menus.unlink()
