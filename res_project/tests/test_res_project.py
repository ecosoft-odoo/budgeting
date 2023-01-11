# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta

from freezegun import freeze_time

from odoo.exceptions import UserError
from odoo.tests.common import Form, TransactionCase


class ResProject(TransactionCase):
    @classmethod
    @freeze_time("2001-02-01")
    def setUpClass(cls):
        super().setUpClass()
        cls.ResProject = cls.env["res.project"]
        cls.ProjectWizard = cls.env["split.project.wizard"]
        cls.dep_admin = cls.env.ref("hr.dep_administration")
        cls.dep_sales = cls.env.ref("hr.dep_sales")
        cls.employee_sale = cls.env.ref("hr.employee_lur")
        cls.today = datetime.today()
        cls.project1 = cls._create_res_project(
            cls,
            "Test Project1",
            cls.dep_admin.id,
            cls.today,
            cls.today,
        )

    def _create_res_project(
        self,
        name,
        department_id,
        date_from,
        date_to,
        code=False,
        parent_project_id=False,
    ):
        return self.ResProject.create(
            {
                "name": name,
                "code": code,
                "parent_project_id": parent_project_id,
                "department_id": department_id,
                "date_from": date_from,
                "date_to": date_to,
            }
        )

    def _create_project_wizard(self, project, new_name=False):
        return self.ProjectWizard.create(
            {
                "parent_project_id": project.parent_project_id.id or project.id,
                "parent_project_name": project.parent_project_name,
                "date_from": project.date_from,
                "date_to": project.date_to,
                "project_manager_id": project.project_manager_id.id,
                "department_id": project.department_id.id,
                "line_ids": [(0, 0, {"project_name": new_name})] if new_name else [],
            }
        )

    @freeze_time("2001-02-01")
    def test_01_project_standard(self):
        """Test normally process project"""
        self.assertEqual(self.project1.name, "Test Project1")
        self.assertEqual(self.project1.parent_project_name, "Test Project1")
        self.assertFalse(self.project1.code)
        # Change name project, parent project should change it too
        self.project1.name = "Test new project"
        self.assertEqual(self.project1.name, "Test new project")
        self.assertEqual(self.project1.parent_project_name, "Test new project")
        # Duplicate project, it should have (copy) at last
        project_copy = self.project1.copy()
        self.assertEqual(project_copy.name, "Test new project (copy)")
        self.assertEqual(project_copy.parent_project_name, "Test new project (copy)")
        # Check department should be change following project manager
        self.assertEqual(self.project1.department_id, self.dep_admin)
        with Form(self.project1) as p:
            p.project_manager_id = self.employee_sale
        p.save()
        self.assertEqual(self.project1.department_id, self.dep_sales)
        # Check plan amount when add it in project
        self.assertFalse(self.project1.plan_amount)
        self.project1.project_plan_ids.create(
            {
                "project_id": self.project1.id,
                "date_from": self.today,
                "date_to": self.today,
                "amount": 100.0,
            }
        )
        self.assertEqual(self.project1.plan_amount, 100.0)
        self.project1.action_cancel()
        self.assertEqual(self.project1.state, "cancel")
        self.project1.action_draft()
        self.assertEqual(self.project1.state, "draft")
        self.project1.action_confirm()
        self.assertEqual(self.project1.state, "confirm")
        # Check auto close project, if today is more than date to
        self.project1.action_auto_expired()
        self.assertEqual(self.project1.state, "confirm")
        yesterday = self.today - timedelta(days=1)
        self.project1.date_to = yesterday
        self.project1.action_auto_expired()
        self.assertEqual(self.project1.state, "close")
        # Check name search with code
        res = self.project1.name_search("0001")
        self.assertFalse(res)
        self.project1.code = "C_TEST000001"
        res = self.project1.name_search("0001")
        self.assertTrue(res)

    @freeze_time("2001-02-01")
    def test_02_split_project(self):
        """add code project and search"""
        self.project2 = self.project1.copy()
        projects = self.project1 + self.project2
        # Not allow split multi project
        with self.assertRaises(UserError):
            self.ResProject.with_context(active_ids=projects.ids).action_split_project()
        split_project_wizard = self.ResProject.with_context(
            active_ids=self.project1.ids
        ).action_split_project()
        self.assertEqual(split_project_wizard["res_model"], "split.project.wizard")
        # Create new wizard for split project
        self.assertTrue(self.project1.active)
        project_wizard = self._create_project_wizard(self.project1)
        with self.assertRaises(UserError):
            project_wizard.split_project()
        project_wizard = self._create_project_wizard(self.project1, "new split1")
        new_project_list = project_wizard.split_project()
        new_project = self.ResProject.browse(new_project_list["domain"][0][2])
        # Parent project will archive when split project
        self.assertFalse(self.project1.active)
        self.assertEqual(new_project.name, "new split1")
        self.assertEqual(new_project.parent_project_id, self.project1)
        self.assertEqual(new_project.parent_project_name, self.project1.name)
