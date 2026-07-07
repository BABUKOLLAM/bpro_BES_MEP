from odoo import models

# Menu URLs kept on a fresh client portal. Everything else from Odoo's
# website starter kit (Services, Pricing, About Us, Jobs, News, ...) is
# marketing placeholder content this backend HR/LMS platform doesn't need.
KEEP_MENU_URLS = {"/", "/slides"}

# Odoo's website module bakes these literal demo strings into whichever
# header/footer views get COW'd for a site's initial setup (e.g. bpro
# Corporate's own site on first install). They aren't tied to any field
# we can just blank out, so any per-website view containing one of them
# gets the offending block stripped out below.
STARTER_MARKERS = ("555-555-5556", "yourcompany.example.com", "Executive Park")


class Website(models.Model):
    _inherit = "website"

    def _bpro_strip_starter_content(self):
        """Send visitors straight to login instead of Odoo's generic
        'Your Company' starter homepage, drop the placeholder marketing
        pages/menu items that come with the website module, and scrub
        any leftover fake contact details (phone/email/address) baked
        into that site's own header/footer views."""
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
            site._bpro_scrub_fake_contact_details()

    def _bpro_scrub_fake_contact_details(self):
        View = self.env["ir.ui.view"].sudo()
        for site in self:
            views = View.search([("website_id", "=", site.id)])
            for view in views:
                arch = view.arch_db
                if not arch or not any(m in arch for m in STARTER_MARKERS):
                    continue
                view.write({"arch_db": self._bpro_drop_marker_blocks(arch)})

    @staticmethod
    def _bpro_drop_marker_blocks(arch):
        """Remove the smallest <p>/<div>/<li>/<ul> ancestor around each
        placeholder marker, since the fake contact details are always
        wrapped in one of those and never worth keeping partially."""
        import re

        for marker in STARTER_MARKERS:
            while marker in arch:
                idx = arch.find(marker)
                tag_start = None
                for tag in ("<li", "<p ", "<p>", "<div"):
                    pos = arch.rfind(tag, 0, idx)
                    if pos != -1 and (tag_start is None or pos > tag_start):
                        tag_start = pos
                if tag_start is None:
                    break
                tag_name = re.match(r"<(\w+)", arch[tag_start:]).group(1)
                depth = 0
                pos = tag_start
                end = None
                for m in re.finditer(rf"</?{tag_name}\b[^>]*>", arch[tag_start:]):
                    depth += 1 if not m.group().startswith("</") else -1
                    if depth == 0:
                        end = tag_start + m.end()
                        break
                if end is None:
                    break
                arch = arch[:tag_start] + arch[end:]
        return arch
