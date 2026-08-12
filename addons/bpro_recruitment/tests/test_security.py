from .common import RecruitmentTestCommon


class TestRecruitmentSecurity(RecruitmentTestCommon):
    """R4.6: read-only HOD visibility scoped to their own department's
    recruitment pipeline and onboarding, while HR/recruitment roles that
    already had full/company-wide access keep it (the ir.rule OR-of-rows
    behavior bpro_recruitment_security.xml's comment documents)."""

    def test_hod_sees_only_own_department_vacancy_requests(self):
        own = self._make_vacancy_request(department_id=self.department.id)
        other = self._make_vacancy_request(department_id=self.other_department.id)
        visible = self.env["bpro.vacancy.request"].with_user(self.hod_user).search([
            ("id", "in", (own | other).ids)
        ])
        self.assertEqual(visible, own)

    def test_hr_sees_vacancy_requests_across_departments(self):
        own = self._make_vacancy_request(department_id=self.department.id)
        other = self._make_vacancy_request(department_id=self.other_department.id)
        visible = self.env["bpro.vacancy.request"].with_user(self.hr_user).search([
            ("id", "in", (own | other).ids)
        ])
        self.assertEqual(visible, own | other)

    def test_hod_sees_only_own_department_job_offers(self):
        own_offer = self._make_offer(
            applicant=self._make_applicant(job=self._make_job(department=self.department))
        )
        other_offer = self._make_offer(
            applicant=self._make_applicant(job=self._make_job(department=self.other_department))
        )
        visible = self.env["bpro.job.offer"].with_user(self.hod_user).search([
            ("id", "in", (own_offer | other_offer).ids)
        ])
        self.assertEqual(visible, own_offer)

    def test_recruitment_manager_sees_job_offers_across_departments(self):
        own_offer = self._make_offer(
            applicant=self._make_applicant(job=self._make_job(department=self.department))
        )
        other_offer = self._make_offer(
            applicant=self._make_applicant(job=self._make_job(department=self.other_department))
        )
        visible = self.env["bpro.job.offer"].with_user(self.hr_user).search([
            ("id", "in", (own_offer | other_offer).ids)
        ])
        self.assertEqual(visible, own_offer | other_offer)

    def test_hod_sees_only_own_department_joining_reports(self):
        own_employee = self.env["hr.employee"].create({
            "name": "Own Dept Joiner", "company_id": self.company.id,
            "department_id": self.department.id,
        })
        other_employee = self.env["hr.employee"].create({
            "name": "Other Dept Joiner", "company_id": self.company.id,
            "department_id": self.other_department.id,
        })
        own_report = self.env["bpro.joining.report"].create({
            "employee_id": own_employee.id, "expected_joining_date": "2026-09-01",
        })
        other_report = self.env["bpro.joining.report"].create({
            "employee_id": other_employee.id, "expected_joining_date": "2026-09-01",
        })
        visible = self.env["bpro.joining.report"].with_user(self.hod_user).search([
            ("id", "in", (own_report | other_report).ids)
        ])
        self.assertEqual(visible, own_report)

    def test_hod_sees_only_own_department_employee_assets(self):
        own_employee = self.env["hr.employee"].create({
            "name": "Own Dept Asset Holder", "company_id": self.company.id,
            "department_id": self.department.id,
        })
        other_employee = self.env["hr.employee"].create({
            "name": "Other Dept Asset Holder", "company_id": self.company.id,
            "department_id": self.other_department.id,
        })
        own_asset = self.env["bpro.employee.asset"].create({
            "employee_id": own_employee.id, "name": "Laptop A",
        })
        other_asset = self.env["bpro.employee.asset"].create({
            "employee_id": other_employee.id, "name": "Laptop B",
        })
        visible = self.env["bpro.employee.asset"].with_user(self.hod_user).search([
            ("id", "in", (own_asset | other_asset).ids)
        ])
        self.assertEqual(visible, own_asset)
