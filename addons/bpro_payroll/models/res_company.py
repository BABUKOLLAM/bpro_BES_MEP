from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    # Seed defaults reflect EPFO's wage ceiling and rates as commonly
    # published — verify against the current EPFO notification before
    # go-live, and revisit whenever EPFO changes them. Nothing below is
    # hardcoded into rule logic; every rate lives here so a change is a
    # data edit, not a code change.
    pf_wage_ceiling = fields.Float(
        string="PF Wage Ceiling (Monthly)",
        default=15000.0,
        help="Statutory PF wage ceiling. EPS and EDLI are always computed "
        "on wages capped at this ceiling, regardless of the employee/"
        "employer PF calculation basis.",
    )
    pf_employee_rate = fields.Float(string="Employee PF Rate (%)", default=12.0)
    pf_employer_rate = fields.Float(
        string="Employer PF Rate (%)",
        default=12.0,
        help="Total employer contribution rate. The EPS share is carved "
        "out of this; the remainder goes to EPF.",
    )
    pf_employer_eps_rate = fields.Float(
        string="Employer EPS Rate (%)",
        default=8.33,
        help="Share of the employer's PF contribution routed to the "
        "Employees' Pension Scheme, always on wages capped at "
        "pf_wage_ceiling.",
    )
    pf_edli_rate = fields.Float(
        string="EDLI Rate (%)",
        default=0.5,
        help="Employer's Deposit Linked Insurance contribution, on wages "
        "capped at pf_wage_ceiling.",
    )
    pf_admin_charge_rate = fields.Float(
        string="EPF Admin Charge Rate (%)",
        default=0.5,
        help="Employer's EPF administrative charge, on wages capped at "
        "pf_wage_ceiling. Some EPFO notifications have applied a minimum "
        "monthly charge floor per establishment rather than a pure "
        "percentage - that floor is NOT modelled here; verify current "
        "applicability before go-live.",
    )

    # ESI seed defaults reflect the rates in force since July 2019 (0.75%
    # employee / 3.25% employer) and the commonly published ₹21,000 gross
    # wage threshold - verify against the current ESIC notification before
    # go-live. Unlike PF, ESI is computed on GROSS wages, not just Basic.
    esi_wage_threshold = fields.Float(
        string="ESI Gross Wage Threshold (Monthly)",
        default=21000.0,
        help="An employee is ESI-covered only if gross wages for the month "
        "are at or below this. NOTE: this implementation re-checks the "
        "threshold every payslip - it does NOT implement ESI's "
        "contribution-period continuity rule (once covered at the start "
        "of an April-September or October-March period, an employee "
        "stays covered for that whole period even if a mid-period raise "
        "pushes gross above the threshold). That's a known gap, not an "
        "oversight - flag it before this goes live for an employee near "
        "the threshold.",
    )
    esi_employee_rate = fields.Float(string="Employee ESI Rate (%)", default=0.75)
    esi_employer_rate = fields.Float(string="Employer ESI Rate (%)", default=3.25)

    tan = fields.Char(
        string="TAN",
        help="Tax Deduction and Collection Account Number - shown on Form "
        "16. Required for actually filing TDS returns with the "
        "government (TRACES portal), which is outside this build's "
        "scope; this field only supports printing it on the document.",
    )
