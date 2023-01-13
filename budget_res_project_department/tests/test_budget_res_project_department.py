# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

from freezegun import freeze_time

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import Form

from odoo.addons.budget_control.tests.common import BudgetControlCommon
from odoo.addons.res_project.tests.common import ResProjectCommon


@tagged("post_install", "-at_install")
class TestBudgetResProjectDepartment(ResProjectCommon, BudgetControlCommon):
    @classmethod
    @freeze_time("2001-02-01")
    def setUpClass(cls):
        super().setUpClass()
        cls.gen_analytic_wizard = cls.env["generate.analytic.account"]
        cls.Analytic = cls.env["account.analytic.account"]
        cls.analytic_group_project = cls.env.ref(
            "budget_res_project_department.analytic_group_project"
        )
        cls.analytic_group_department = cls.env.ref(
            "budget_res_project_department.analytic_group_department"
        )

    @freeze_time("2001-02-01")
    def test_01_create_analytic_from_project(self):
        today = datetime.today()
        project = self._create_res_project(
            "Test Project1",
            self.dep_admin.id,
            today,
            today,
        )
        # Check project must be state confirm, will create generate analytic
        self.assertEqual(project.state, "draft")
        with self.assertRaises(UserError):
            with Form(
                self.gen_analytic_wizard.with_context(
                    active_model=project._name, active_ids=project.ids
                )
            ) as wiz:
                wiz.budget_period_id = self.budget_period
        project.action_confirm()
        self.assertEqual(project.state, "confirm")
        # Generate analytic from project
        with Form(
            self.gen_analytic_wizard.with_context(
                active_model=project._name, active_ids=project.ids
            )
        ) as wiz:
            wiz.budget_period_id = self.budget_period
        generate_wiz = wiz.save()
        self.assertEqual(generate_wiz.bm_date_from, self.budget_period.bm_date_from)
        self.assertEqual(generate_wiz.bm_date_to, self.budget_period.bm_date_to)
        self.assertFalse(generate_wiz.analytic_ids)
        self.assertEqual(generate_wiz.group_id, self.analytic_group_project)
        res = generate_wiz.action_create_analytic()
        # Check analytic from project
        analytic = self.Analytic.browse(res["domain"][0][2])
        self.assertEqual(analytic.project_id, project)
        self.assertTrue(analytic.is_required_project)
        self.assertFalse(analytic.is_required_department)
        # Check select project is not confirm in analytic, it should not selected
        project_not_confirm = self._create_res_project(
            "Test Project2",
            self.dep_admin.id,
            today,
            today,
        )
        with self.assertRaises(UserError):
            with Form(analytic) as aa:
                aa.project_id = project_not_confirm
        # Check select department and project in analytic, it should not selected
        with self.assertRaises(UserError):
            with Form(analytic) as aa:
                aa.department_id = self.dep_admin
        # Check create new analytic with project is not confirm, it should not selected
        with self.assertRaises(UserError):
            self.Analytic.create(
                {
                    "name": "Analytic Test",
                    "group_id": self.analytic_group_project.id,
                    "project_id": project_not_confirm.id,
                }
            )
        # Check create new analytic with project and department in analytic,
        # it should not selected
        with self.assertRaises(UserError):
            self.Analytic.create(
                {
                    "name": "Analytic Test",
                    "project_id": project.id,
                    "department_id": self.dep_admin.id,
                }
            )

    @freeze_time("2001-02-01")
    def test_02_create_analytic_from_department(self):
        # Generate analytic from admin department
        with Form(
            self.gen_analytic_wizard.with_context(
                active_model=self.dep_admin._name, active_ids=self.dep_admin.ids
            )
        ) as wiz:
            wiz.budget_period_id = self.budget_period
        generate_wiz = wiz.save()
        self.assertEqual(generate_wiz.bm_date_from, self.budget_period.bm_date_from)
        self.assertEqual(generate_wiz.bm_date_to, self.budget_period.bm_date_to)
        self.assertFalse(generate_wiz.analytic_ids)
        self.assertEqual(generate_wiz.group_id, self.analytic_group_department)
        res = generate_wiz.action_create_analytic()
        # Check analytic from department
        analytic = self.Analytic.browse(res["domain"][0][2])
        self.assertEqual(analytic.department_id, self.dep_admin)
        self.assertTrue(analytic.is_required_department)
        self.assertFalse(analytic.is_required_project)
        # Check create analytic with same department and period again,
        # it should not generate new analytic
        with Form(
            self.gen_analytic_wizard.with_context(
                active_model=self.dep_admin._name, active_ids=self.dep_admin.ids
            )
        ) as wiz:
            wiz.budget_period_id = self.budget_period
        generate_wiz = wiz.save()
        res = generate_wiz.action_create_analytic()
        self.assertFalse(res["domain"][0][2])
        # Test find next analytic, create new analytic without data
        next_analytic = analytic.next_year_analytic()
        self.assertNotEqual(analytic, next_analytic)

    @freeze_time("2001-02-01")
    def test_03_check_budget_control(self):
        # Generate analytic from admin department
        with Form(
            self.gen_analytic_wizard.with_context(
                active_model=self.dep_admin._name, active_ids=self.dep_admin.ids
            )
        ) as wiz:
            wiz.budget_period_id = self.budget_period
        generate_wiz = wiz.save()
        res = generate_wiz.action_create_analytic()
        analytic = self.Analytic.browse(res["domain"][0][2])
        # Create Budget Control and check department following department
        budget_control = self.BudgetControl.create(
            {
                "name": "CostCenter1/%s" % self.year,
                "template_id": self.budget_period.template_id.id,
                "budget_period_id": self.budget_period.id,
                "analytic_account_id": analytic.id,
                "plan_date_range_type_id": self.date_range_type.id,
                "allocated_amount": 2400.0,
                "template_line_ids": [
                    self.template_line1.id,
                    self.template_line2.id,
                    self.template_line3.id,
                ],
            }
        )
        # Test item created for 3 kpi x 4 quarters = 12 budget items
        budget_control.prepare_budget_control_matrix()
        assert len(budget_control.line_ids) == 12
        # Assign budget.control amount: KPI1 = 100x4=400, KPI2=800, KPI3=1,200
        budget_control.line_ids.filtered(lambda x: x.kpi_id == self.kpi1).write(
            {"amount": 100}
        )
        budget_control.line_ids.filtered(lambda x: x.kpi_id == self.kpi2).write(
            {"amount": 200}
        )
        budget_control.line_ids.filtered(lambda x: x.kpi_id == self.kpi3).write(
            {"amount": 300}
        )
        budget_control.flush()
        # Control budget
        self.budget_period.control_budget = True
        budget_control.action_done()
        # Commit budget, check department
        bill1 = self._create_simple_bill(analytic, self.account_kpi1, 400)
        bill1.action_post()
        self.assertEqual(bill1.budget_move_ids.department_id, self.dep_admin)
