from odoo import fields, models


class BproPtConfig(models.Model):
    _name = "bpro.pt.config"
    _description = "Professional Tax Configuration (per state)"

    name = fields.Char(required=True, help="e.g. 'Karnataka'")
    state_id = fields.Many2one(
        "res.country.state", string="State", required=True
    )
    periodicity = fields.Selection(
        [("monthly", "Monthly"), ("half_yearly", "Half-Yearly")],
        required=True,
        help="Monthly states levy PT every payslip. Half-yearly states "
        "(Tamil Nadu, Kerala) levy a single lump sum twice a year, based "
        "on accumulated half-year income - see charge_month_h1/h2.",
    )
    charge_month_h1 = fields.Selection(
        [(str(i), m) for i, m in enumerate(
            ["January", "February", "March", "April", "May", "June",
             "July", "August", "September", "October", "November", "December"],
            start=1,
        )],
        string="H1 Charge Month (Apr-Sep period)",
        help="Half-yearly only: the month the April-September period's PT "
        "lump sum is actually deducted.",
    )
    charge_month_h2 = fields.Selection(
        [(str(i), m) for i, m in enumerate(
            ["January", "February", "March", "April", "May", "June",
             "July", "August", "September", "October", "November", "December"],
            start=1,
        )],
        string="H2 Charge Month (Oct-Mar period)",
        help="Half-yearly only: the month the October-March period's PT "
        "lump sum is actually deducted.",
    )
    slab_line_ids = fields.One2many("bpro.pt.slab.line", "config_id", string="Slabs")
    note = fields.Text(
        help="Jurisdiction caveats - e.g. Kerala's actual slabs vary by "
        "local body (Panchayat/Municipality/Corporation); confirm which "
        "applies to the client's registered office before go-live.",
    )


class BproPtSlabLine(models.Model):
    _name = "bpro.pt.slab.line"
    _description = "Professional Tax Slab Line"
    _order = "lower_bound"

    config_id = fields.Many2one("bpro.pt.config", required=True, ondelete="cascade")
    lower_bound = fields.Float(required=True)
    upper_bound = fields.Float(
        help="0 means unbounded (this is the top slab)."
    )
    amount = fields.Float(
        required=True,
        help="Monthly states: amount charged per month in this band. "
        "Half-yearly states: lump sum charged for the half-year in this "
        "income band.",
    )
    topup_month = fields.Selection(
        [(str(i), m) for i, m in enumerate(
            ["January", "February", "March", "April", "May", "June",
             "July", "August", "September", "October", "November", "December"],
            start=1,
        )],
        help="Monthly states only: some states charge a higher amount in "
        "one specific month so the annual total lands exactly on the "
        "₹2,500 constitutional cap (e.g. Karnataka charges ₹300 in "
        "February instead of the usual ₹200). Leave blank if this band "
        "has no such adjustment.",
    )
    topup_amount = fields.Float(
        help="Amount charged instead of 'amount' in topup_month."
    )
