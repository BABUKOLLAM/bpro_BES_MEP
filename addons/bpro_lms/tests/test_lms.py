from odoo.tests.common import TransactionCase


class TestLmsAutomation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.corp = cls.env.ref("base.main_company")
        cls.client = cls.env["res.company"].create(
            {"name": "LMS Test Client", "parent_id": cls.corp.id}
        )
        cls.tag_induction = cls.env.ref("bpro_lms.tag_induction")
        cls.tag_policy = cls.env.ref("bpro_lms.tag_policy_updation")
        cls.tag_reinduction = cls.env.ref("bpro_lms.tag_re_induction")
        # global induction course owned by the master company
        cls.course = cls.env["slide.channel"].create(
            {"name": "LMS Test Induction", "company_id": cls.corp.id,
             "tag_ids": [(6, 0, cls.tag_induction.ids)]}
        )
        cls.user = cls.env["res.users"].create(
            {"name": "lms-emp", "login": "lms-emp",
             "company_id": cls.client.id,
             "company_ids": [(6, 0, cls.client.ids)],
             "groups_id": [(4, cls.env.ref("base.group_user").id),
                            (4, cls.env.ref("bpro_base.group_employee").id)]}
        )

    def _membership(self, course, partner):
        return self.env["slide.channel.partner"].search(
            [("channel_id", "=", course.id), ("partner_id", "=", partner.id)]
        )

    def test_new_employee_auto_enrolled_in_induction(self):
        emp = self.env["hr.employee"].create(
            {"name": "lms-emp", "company_id": self.client.id,
             "user_id": self.user.id}
        )
        self.assertTrue(
            self._membership(self.course, emp.user_id.partner_id),
            "new employee must be enrolled in the global induction course",
        )

    def test_policy_course_pushed_on_publish(self):
        emp = self.env["hr.employee"].create(
            {"name": "lms-emp", "company_id": self.client.id,
             "user_id": self.user.id}
        )
        policy = self.env["slide.channel"].create(
            {"name": "LMS Test Policy", "company_id": self.client.id,
             "tag_ids": [(6, 0, self.tag_policy.ids)]}
        )
        self.assertFalse(self._membership(policy, emp.user_id.partner_id))
        policy.is_published = True
        self.assertTrue(
            self._membership(policy, emp.user_id.partner_id),
            "publishing a policy course must enroll the client's employees",
        )

    def test_reinduction_resets_completion(self):
        emp = self.env["hr.employee"].create(
            {"name": "lms-emp", "company_id": self.client.id,
             "user_id": self.user.id}
        )
        self.course.tag_ids = [(4, self.tag_reinduction.id)]
        membership = self._membership(self.course, emp.user_id.partner_id)
        membership.completion = 100
        self.env["hr.employee"]._cron_annual_reinduction()
        membership = self._membership(self.course, emp.user_id.partner_id)
        self.assertEqual(len(membership), 1)
        self.assertEqual(membership.completion, 0)

    def test_goal_training_progress(self):
        emp = self.env["hr.employee"].create(
            {"name": "lms-emp", "company_id": self.client.id,
             "user_id": self.user.id}
        )
        goal = self.env["bpro.pms.goal"].create(
            {"name": "train", "employee_id": emp.id,
             "company_id": self.client.id,
             "course_ids": [(6, 0, self.course.ids)]}
        )
        self.assertEqual(goal.training_progress, 0)
        self._membership(self.course, emp.user_id.partner_id).completion = 50
        goal.invalidate_recordset(["training_progress"])
        self.assertEqual(goal.training_progress, 50)

    def test_appraisal_training_need_auto_enrolls_courses(self):
        emp = self.env["hr.employee"].create(
            {"name": "lms-emp", "company_id": self.client.id,
             "user_id": self.user.id}
        )
        skill_course = self.env["slide.channel"].create(
            {"name": "LMS Skill Course", "company_id": self.client.id}
        )
        comp = self.env["bpro.pms.competency"].create(
            {"name": "LMS Competency", "company_id": self.client.id,
             "course_ids": [(6, 0, skill_course.ids)]}
        )
        cycle = self.env["bpro.pms.cycle"].create(
            {"name": "LMS Cycle", "date_start": "2026-01-01",
             "date_end": "2026-12-31", "company_id": self.client.id}
        )
        appr = self.env["bpro.pms.appraisal"].create(
            {"employee_id": emp.id, "reviewer_id": emp.id,
             "cycle_id": cycle.id, "company_id": self.client.id}
        )
        need = self.env["bpro.pms.training.need"].create(
            {"employee_id": emp.id, "competency_id": comp.id,
             "appraisal_id": appr.id}
        )
        appr.action_done()
        self.assertEqual(need.state, "enrolled")
        self.assertTrue(
            self._membership(skill_course, emp.user_id.partner_id),
            "completing the appraisal must enroll the employee in the "
            "competency's courses",
        )

    def test_training_report_rows(self):
        emp = self.env["hr.employee"].create(
            {"name": "lms-emp", "company_id": self.client.id,
             "user_id": self.user.id}
        )
        rows = self.env["bpro.training.report"].search(
            [("employee_id", "=", emp.id)]
        )
        self.assertTrue(rows, "induction enrollment must appear in the report")
        self.assertEqual(rows.company_id, self.client)
