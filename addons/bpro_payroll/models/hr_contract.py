from odoo import fields, models


class HrContract(models.Model):
    _inherit = "hr.contract"

    ctc_annual = fields.Float(
        string="CTC (Annual)",
        help="Cost to Company for a full year — the figure the India salary "
        "breakup (Basic, HRA, flexible benefits) is derived from. Distinct "
        "from 'wage' (native Odoo's monthly pay figure), which this "
        "structure does not use.",
    )
    basic_percent = fields.Float(
        string="Basic % of CTC",
        default=50.0,
        help="Company policy, not a statutory figure. Commonly kept near "
        "50% because a very low Basic reduces the PF contribution base — "
        "worth revisiting once the PF release (R3.2) is in.",
    )
    hra_percent = fields.Float(
        string="HRA % of Basic",
        default=40.0,
        help="Company policy. Typically 50% for metro cities, 40% for "
        "non-metro — set per contract since this structure doesn't yet "
        "encode a metro/non-metro employee attribute.",
    )
    pf_applicable = fields.Boolean(
        string="PF Applicable",
        default=True,
        help="Uncheck for an employee legitimately excluded from PF "
        "(e.g. certain international workers, or someone who both joined "
        "with basic above the wage ceiling and was never already a PF "
        "member). This does not itself implement EPFO's exclusion "
        "criteria — it's an HR-set override for cases already determined "
        "to qualify.",
    )
    pf_calculation_basis = fields.Selection(
        [
            ("capped", "Capped at Wage Ceiling"),
            ("full_basic", "Full Basic (No Cap)"),
        ],
        string="PF Calculation Basis",
        default="capped",
        help="'Capped' restricts employee/employer PF (not EPS/EDLI, which "
        "are always capped) to the company's PF wage ceiling. 'Full Basic' "
        "is a more generous employer policy contributing on the entire "
        "Basic with no ceiling.",
    )
    esi_applicable = fields.Boolean(
        string="ESI Applicable",
        default=True,
        help="HR override to exclude a specific employee from ESI. The "
        "actual per-payslip eligibility check is gross wages against the "
        "company's ESI threshold - this flag is an additional override on "
        "top of that, not a replacement for it.",
    )
    pt_state_id = fields.Many2one(
        "bpro.pt.config",
        string="PT State",
        help="The state whose Professional Tax slab applies to this "
        "employee - normally their work location's state, not "
        "necessarily the company's registered state. Leave blank for no "
        "PT (e.g. a state with no PT levy at all).",
    )
    lwf_state_id = fields.Many2one(
        "bpro.lwf.config",
        string="LWF State",
        help="The state whose Labour Welfare Fund applies to this "
        "employee. Leave blank if not applicable - e.g. Kerala isn't "
        "seeded by default (its LWF coverage depends on the establishment "
        "type/board, not a single flat state rate); add a bpro.lwf.config "
        "for it once that's confirmed, no code change needed.",
    )
    tds_regime = fields.Selection(
        [("new", "New Regime"), ("old", "Old Regime")],
        default="new",
        help="Employee's declared regime for TDS purposes - optional per "
        "employee, either is valid. Under actual tax law this can only be "
        "changed once at the start of each financial year; this field "
        "doesn't enforce that, review it at each FY start.",
    )
