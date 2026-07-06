from odoo import fields, models


class SlideChannel(models.Model):
    """Content ownership per the roadmap: a course owned by bpro Corporate
    (the parent company) is global and visible to every client company;
    a course owned by a client company stays private to that client."""

    _inherit = "slide.channel"

    company_id = fields.Many2one(
        "res.company",
        string="Owner Company",
        default=lambda self: self.env.company,
        help="Global courses (Induction, Compliance, Policy) belong to "
        "bpro Corporate and are visible to all client companies. "
        "Client-specific courses stay private to that client.",
    )
