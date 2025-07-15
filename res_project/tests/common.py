# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase


class ResProjectCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ResProject = cls.env["res.project"]
        cls.ProjectWizard = cls.env["split.project.wizard"]
        cls.dep_admin = cls.env.ref("hr.dep_administration")
        cls.dep_sales = cls.env.ref("hr.dep_sales")
        cls.employee_sale = cls.env.ref("hr.employee_lur")

    def _create_res_project(
        self,
        name,
        department_id,
        date_from,
        date_to,
        code="/",
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
