{
    "name": "bpro Recruitment — Vacancy Requests & Hiring Workflow",
    "summary": "HOD vacancy requisition + interview evaluation + offer/acceptance portal + hiring finalization on top of native Recruitment (BES HR module, R4.1-4.4)",
    "description": """
Recruitment build-out for the India client, layered on top of native
Odoo Recruitment rather than replacing it: job posting, the public
application page, applicant pipeline stages, interviewer assignment, and
interview scheduling (hr.applicant.meeting_ids -> calendar.event) are
all native (hr_recruitment + website_hr_recruitment) and untouched here
- this module only adds what's genuinely missing.

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

R4.2 - interview evaluation:

* New model bpro.interview.evaluation (one2many from hr.applicant, one
  record per interviewer per round - a panel can each submit
  independent feedback): interviewer, online/offline type, datetime,
  marks, remarks, and the exact recommendation vocabulary requested -
  Recommended for Selection / On Hold / Rejected / No Comments (default)
  - distinct from native's generic 3-star priority field.
* Creating an evaluation adds the interviewer to the applicant's native
  interviewer_ids if not already there, piggybacking on hr_recruitment's
  own notification-on-assignment hook rather than duplicating it.
* Separately notifies the requesting department's HOD via the
  applicant's chatter (message_post) - native only notifies the
  interviewer themselves, not a HOD who may not be on the panel. Closes
  the "intimated to interview panel/HOD or concerned" requirement.

R4.3 - offer letter + candidate acceptance portal:

* New model bpro.job.offer (inherits portal.mixin for the standard
  access_token pattern Odoo itself uses for share links - not a custom
  auth scheme): proposed designation/CTC/joining date, plus fields the
  CANDIDATE fills in themselves (address, DOB, PAN, Aadhar, emergency
  contact, bank details) - draft -> sent -> accepted/declined workflow.
* "Send Offer" emails the candidate a tokenised link
  (/bpro/offer/<id>?access_token=...). WhatsApp was explicitly deferred
  in the 2026-08-12 scoping decision pending the client's WhatsApp
  Business API credentials - this is the one place a WhatsApp send would
  plug in alongside the email, not a rebuild, once that account exists.
* Public portal page (auth="public", the token IS the authentication):
  shows the offer summary, an editable form for the candidate's details,
  and Accept/Decline buttons - no login required, matching how the
  public job-application page itself works.
* Offer letter PDF report, following the bpro.tds.form16 QWeb pattern
  from the payroll build.

R4.4 - hiring finalization:

* Adds employee_code to hr.employee (unique, auto-assigned, never
  reused) via a new ir.sequence 'bpro.employee.code' (EMP00001 style).
  Not company-scoped - each bpro-lms-pms client gets its own database
  (per that repo's own README), so there's no cross-client collision to
  guard against with company scoping.
* bpro.job.offer's "Finalize Hiring" action (accepted state only, once
  per offer - re-finalizing raises with the existing employee's name and
  code) reuses native hr_recruitment's own
  applicant_id.create_employee_from_applicant() to create the hr.employee
  rather than duplicating that logic, then assigns the employee_code and
  links employee_id back onto the offer. Gated to
  hr_recruitment.group_hr_recruitment_manager - the "final approval of
  the HR Dept" the requirement describes - with a confirmation prompt
  since it's irreversible.
* Appointment Order PDF report (employee code, name, designation,
  department, joining date, CTC), same QWeb pattern as the offer letter
  and bpro.tds.form16 from payroll.

Later releases (not in this one): joining/onboarding SLA (R4.5),
HOD/management reporting (R4.6).
""",
    "version": "18.0.1.3.0",
    "category": "Human Resources",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": [
        "bpro_base",
        "bpro_hr",
        "hr_recruitment",
        "website_hr_recruitment",
        "portal",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/bpro_recruitment_security.xml",
        "data/bpro_employee_code_sequence.xml",
        "views/bpro_vacancy_request_views.xml",
        "views/bpro_interview_evaluation_views.xml",
        "views/report_job_offer.xml",
        "views/report_appointment_order.xml",
        "views/bpro_job_offer_views.xml",
        "views/portal_offer_templates.xml",
    ],
    "installable": True,
    "application": False,
}
