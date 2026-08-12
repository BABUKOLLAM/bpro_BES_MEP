{
    "name": "bpro Recruitment — Vacancy Requests & Hiring Workflow",
    "summary": "HOD vacancy requisition/approval on top of native Recruitment (BES HR module, R4.1)",
    "description": """
Recruitment build-out for the India client, layered on top of native
Odoo Recruitment rather than replacing it: job posting, the public
application page, applicant pipeline stages, and interviewer assignment
are all native (hr_recruitment + website_hr_recruitment) and untouched
here - this module only adds what's genuinely missing.

R4.1 - vacancy request + job portal foundation:

* New model bpro.vacancy.request: a Head of Department requests a new
  position (department, job title, headcount, justification, target
  date). draft -> submitted -> approved/rejected workflow. Reuses
  bpro_base's existing four-tier security (group_hod scoped to
  department_id.manager_id.user_id, group_client_hr as approver) rather
  than inventing a parallel role model.
* On approval, auto-creates (or links to) the corresponding hr.job
  record, ready to be published via the native website_hr_recruitment
  public application page - no separate "publish" step needed.
* Rejecting a request does NOT create a job. A request can be resubmitted
  after rejection.

Later releases (not in this one): custom interview recommendation
status (R4.2), offer letter + candidate acceptance portal (R4.3),
employee code + Appointment Order generation (R4.4), joining/onboarding
SLA (R4.5), HOD/management reporting (R4.6).
""",
    "version": "18.0.1.0.0",
    "category": "Human Resources",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": [
        "bpro_base",
        "bpro_hr",
        "hr_recruitment",
        "website_hr_recruitment",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/bpro_recruitment_security.xml",
        "views/bpro_vacancy_request_views.xml",
    ],
    "installable": True,
    "application": False,
}
