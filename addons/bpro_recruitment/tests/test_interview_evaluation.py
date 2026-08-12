from .common import RecruitmentTestCommon


class TestInterviewEvaluation(RecruitmentTestCommon):
    """R4.2: creating an evaluation piggybacks on native interviewer_ids
    and separately notifies the requesting department's HOD, since native
    hr_recruitment only notifies the assigned interviewer."""

    def test_create_adds_the_interviewer_to_the_applicants_interviewer_ids(self):
        applicant = self._make_applicant(job=self._make_job())
        self.assertNotIn(self.hr_user, applicant.interviewer_ids)
        self.env["bpro.interview.evaluation"].create({
            "applicant_id": applicant.id,
            "interviewer_id": self.hr_user.id,
            "recommendation": "recommended",
        })
        self.assertIn(self.hr_user, applicant.interviewer_ids)

    def test_create_does_not_duplicate_an_existing_interviewer(self):
        applicant = self._make_applicant(job=self._make_job())
        applicant.interviewer_ids = [(4, self.hr_user.id)]
        before_count = len(applicant.interviewer_ids)
        self.env["bpro.interview.evaluation"].create({
            "applicant_id": applicant.id,
            "interviewer_id": self.hr_user.id,
            "recommendation": "on_hold",
        })
        self.assertEqual(len(applicant.interviewer_ids), before_count)

    def test_create_notifies_the_departments_hod(self):
        job = self._make_job(department=self.department)
        applicant = self._make_applicant(job=job)
        before_messages = applicant.message_ids
        evaluation = self.env["bpro.interview.evaluation"].create({
            "applicant_id": applicant.id,
            "interviewer_id": self.hr_user.id,
            "interview_type": "online",
            "recommendation": "no_comments",
        })
        new_messages = applicant.message_ids - before_messages
        notified_partners = new_messages.mapped("partner_ids")
        self.assertIn(self.hod_user.partner_id, notified_partners)
        self.assertIn(self.hr_user.name, "".join(new_messages.mapped("body")))
        self.assertTrue(evaluation)

    def test_no_notification_error_when_department_has_no_manager(self):
        department_without_hod = self.env["hr.department"].create({
            "name": "No Manager Dept", "company_id": self.company.id,
        })
        job = self._make_job(department=department_without_hod)
        applicant = self._make_applicant(job=job)
        # Must not raise even though department_id.manager_id.user_id is empty.
        evaluation = self.env["bpro.interview.evaluation"].create({
            "applicant_id": applicant.id,
            "interviewer_id": self.hr_user.id,
            "recommendation": "rejected",
        })
        self.assertTrue(evaluation)
