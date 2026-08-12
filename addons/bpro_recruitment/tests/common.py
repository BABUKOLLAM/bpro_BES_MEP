import itertools

from odoo.tests.common import TransactionCase

_job_name_counter = itertools.count(1)


class RecruitmentTestCommon(TransactionCase):
    """Shared fixture: one department with an HOD, an HR/recruitment-manager
    user, and helpers to build a vacancy request or a hireable applicant
    without repeating the same setup across every test file."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        internal_user = cls.env.ref("base.group_user")

        cls.department = cls.env["hr.department"].create({
            "name": "Recruitment Test Dept", "company_id": cls.company.id,
        })
        cls.other_department = cls.env["hr.department"].create({
            "name": "Recruitment Test Dept (Other)", "company_id": cls.company.id,
        })

        cls.hod_user = cls.env["res.users"].create({
            "name": "Recruitment Test HOD", "login": "bpro_recruit_hod",
            "email": "bpro_recruit_hod@example.com",
            "company_id": cls.company.id,
            "company_ids": [(6, 0, [cls.company.id])],
            "groups_id": [(6, 0, (
                cls.env.ref("bpro_base.group_hod") | internal_user
            ).ids)],
        })
        cls.hod_employee = cls.env["hr.employee"].create({
            "name": "Recruitment Test HOD Employee", "company_id": cls.company.id,
            "department_id": cls.department.id, "user_id": cls.hod_user.id,
        })
        cls.department.manager_id = cls.hod_employee

        cls.other_hod_user = cls.env["res.users"].create({
            "name": "Recruitment Test Other HOD", "login": "bpro_recruit_other_hod",
            "email": "bpro_recruit_other_hod@example.com",
            "company_id": cls.company.id,
            "company_ids": [(6, 0, [cls.company.id])],
            "groups_id": [(6, 0, (
                cls.env.ref("bpro_base.group_hod") | internal_user
            ).ids)],
        })
        cls.other_hod_employee = cls.env["hr.employee"].create({
            "name": "Recruitment Test Other HOD Employee", "company_id": cls.company.id,
            "department_id": cls.other_department.id, "user_id": cls.other_hod_user.id,
        })
        cls.other_department.manager_id = cls.other_hod_employee

        cls.hr_user = cls.env["res.users"].create({
            "name": "Recruitment Test HR", "login": "bpro_recruit_hr",
            "email": "bpro_recruit_hr@example.com",
            "company_id": cls.company.id,
            "company_ids": [(6, 0, [cls.company.id])],
            "groups_id": [(6, 0, (
                cls.env.ref("bpro_base.group_client_hr")
                | cls.env.ref("hr_recruitment.group_hr_recruitment_manager")
                | internal_user
            ).ids)],
        })

    def _make_vacancy_request(self, **kwargs):
        vals = {
            "department_id": self.department.id,
            "job_title": "Test Position",
            "positions_count": 1,
            "justification": "Backfill for a departing team member.",
        }
        vals.update(kwargs)
        return self.env["bpro.vacancy.request"].create(vals)

    def _make_job(self, department=None, **kwargs):
        # hr.job has a (name, company_id, department_id) unique constraint -
        # a bare "Test Job" default collides the moment a test creates two
        # jobs in the same department.
        vals = {
            "name": f"Test Job {next(_job_name_counter)}",
            "department_id": (department or self.department).id,
            "company_id": self.company.id,
        }
        vals.update(kwargs)
        return self.env["hr.job"].create(vals)

    def _make_applicant(self, job=None, email_from="candidate@example.com", **kwargs):
        # hr.applicant.candidate_id is required, but partner_name/email_from
        # are a non-stored inverse field and a related field respectively -
        # both need candidate_id to already exist, so passing them straight
        # into hr.applicant.create() without a candidate_id hits a NOT NULL
        # violation before the inverse ever runs. Create the candidate first,
        # same as the public application form and _inverse_name() itself do.
        candidate = self.env["hr.candidate"].create({
            "partner_name": "Test Candidate",
            "email_from": email_from,
        })
        vals = {
            "candidate_id": candidate.id,
            "job_id": (job or self._make_job()).id,
        }
        vals.update(kwargs)
        return self.env["hr.applicant"].create(vals)

    def _make_offer(self, applicant=None, **kwargs):
        vals = {
            "applicant_id": (applicant or self._make_applicant()).id,
            "proposed_designation": "Test Designation",
            "proposed_ctc": 600000.0,
            "joining_date": "2026-09-01",
        }
        vals.update(kwargs)
        return self.env["bpro.job.offer"].create(vals)
