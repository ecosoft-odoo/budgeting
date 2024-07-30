# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

from freezegun import freeze_time

from odoo.addons.res_project.tests.common import ResProjectCommon


class ResProjectSequence(ResProjectCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    @freeze_time("2001-02-01")
    def test_01_project_sequence(self):
        # Check code in project
        today = datetime.today()
        project = self._create_res_project(
            "Test Project1",
            self.dep_admin.id,
            today,
            today,
            code="/",
        )
        self.assertNotEqual(project.code, "/")
        # Check code in split project
        project_wizard = self._create_project_wizard(project, "new split1")
        new_project_list = project_wizard.split_project()
        new_project = self.ResProject.browse(new_project_list["domain"][0][2])
        self.assertEqual(new_project.code, "{}-1".format(project.code))
