from odoo import fields, models


class BproTdsRegimeConfig(models.Model):
    _name = "bpro.tds.regime.config"
    _description = "TDS Regime Configuration (per financial year)"
    _order = "fy_start_year desc, regime"

    name = fields.Char(required=True, help="e.g. 'New Regime FY2026-27'")
    regime = fields.Selection(
        [("new", "New Regime"), ("old", "Old Regime")], required=True
    )
    fy_start_year = fields.Integer(
        required=True,
        help="The calendar year the financial year STARTS in - FY2026-27 "
        "(1 Apr 2026 - 31 Mar 2027) is fy_start_year=2026.",
    )
    standard_deduction = fields.Float(required=True)
    rebate_income_threshold = fields.Float(
        string="87A Rebate Income Threshold",
        help="If projected annual taxable income is at or below this, "
        "the Section 87A rebate (up to rebate_max_amount) zeroes out the "
        "tax. Does not implement marginal relief for income just above "
        "this threshold - a known simplification.",
    )
    rebate_max_amount = fields.Float(string="87A Rebate Max Amount")
    cess_rate = fields.Float(
        string="Health & Education Cess (%)",
        default=4.0,
        help="Applied to tax after the 87A rebate. Does not implement "
        "surcharge for very high incomes (>50L/1Cr etc.) - a known gap, "
        "flag if the client has employees in that range.",
    )
    slab_line_ids = fields.One2many(
        "bpro.tds.slab.line", "config_id", string="Slabs"
    )
    note = fields.Text()


class BproTdsSlabLine(models.Model):
    _name = "bpro.tds.slab.line"
    _description = "TDS Tax Slab Line"
    _order = "lower_bound"

    config_id = fields.Many2one(
        "bpro.tds.regime.config", required=True, ondelete="cascade"
    )
    lower_bound = fields.Float(required=True)
    upper_bound = fields.Float(help="0 means unbounded (top slab).")
    rate = fields.Float(required=True, help="Percentage, e.g. 5.0 for 5%.")
