from . import models
from . import wizard


def _post_init_hook(env):
    """Also strip the starter-kit marketing content from every existing
    website (bpro Corporate's own site included), so a fresh production
    install doesn't show Odoo's generic 'Your Company' theme either."""
    sites = env["website"].search([]).sudo()
    sites._bpro_strip_starter_content()
    master_site = sites.filtered(lambda w: not w.company_id.parent_id)
    master_site.write({"name": "bpro LMS + PMS"})

