from odoo import fields, models

_MONTHS = [(str(i), m) for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June",
     "July", "August", "September", "October", "November", "December"],
    start=1,
)]


class BproLwfConfig(models.Model):
    _name = "bpro.lwf.config"
    _description = "Labour Welfare Fund Configuration (per state)"

    name = fields.Char(required=True, help="e.g. 'Karnataka'")
    state_id = fields.Many2one(
        "res.country.state", string="State", required=True
    )
    periodicity = fields.Selection(
        [
            ("annual", "Annual"),
            ("half_yearly", "Half-Yearly"),
            ("monthly", "Monthly"),
        ],
        required=True,
        default="annual",
        help="All states seeded so far (Karnataka, Tamil Nadu, Andhra "
        "Pradesh) are annual. half_yearly/monthly exist so a future state "
        "with a different LWF cycle can be added via this same form, no "
        "code change needed.",
    )
    charge_month_h1 = fields.Selection(
        _MONTHS,
        string="Charge Month",
        help="Annual: the one month LWF is deducted. Half-yearly: the "
        "first period's charge month (mirrors bpro.pt.config's shape).",
    )
    charge_month_h2 = fields.Selection(
        _MONTHS,
        string="Charge Month (2nd half, half-yearly only)",
    )
    slab_line_ids = fields.One2many("bpro.lwf.slab.line", "config_id", string="Amounts")
    note = fields.Text(
        help="Applicability caveats - e.g. which establishment type/board "
        "this covers, source, verification status.",
    )


class BproLwfSlabLine(models.Model):
    _name = "bpro.lwf.slab.line"
    _description = "Labour Welfare Fund Amount Line"
    _order = "lower_bound"

    config_id = fields.Many2one("bpro.lwf.config", required=True, ondelete="cascade")
    lower_bound = fields.Float(
        default=0.0,
        help="Income band this line applies to. For a flat-rate state "
        "(all three seeded so far), leave at 0 with upper_bound 0 "
        "(unbounded) - one line covers everyone.",
    )
    upper_bound = fields.Float(help="0 means unbounded.")
    employee_amount = fields.Float(required=True)
    employer_amount = fields.Float(required=True)
