from odoo import fields, models


class PmsCompetency(models.Model):
    """Shared competency model (roadmap P6). Like courses, a competency
    owned by bpro Corporate is global; one owned by a client company is
    private to that client."""

    _name = "bpro.pms.competency"
    _description = "Competency"
    _order = "name"

    name = fields.Char(string="Competency", required=True)
    description = fields.Text(string="Description")
    company_id = fields.Many2one(
        "res.company",
        string="Owner Company",
        default=lambda self: self.env.company,
        help="Owned by bpro Corporate = shared with all clients.",
    )
    training_need_count = fields.Integer(compute="_compute_training_need_count")

    def _compute_training_need_count(self):
        counts = {
            g["competency_id"][0]: g["competency_id_count"]
            for g in self.env["bpro.pms.training.need"].read_group(
                [("competency_id", "in", self.ids)], ["competency_id"], ["competency_id"]
            )
        }
        for rec in self:
            rec.training_need_count = counts.get(rec.id, 0)
