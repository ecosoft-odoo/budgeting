# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import ast

from freezegun import freeze_time

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.budget_control.tests.common import BudgetControlCommon


@tagged("post_install", "-at_install")
class TestBudgetControl(BudgetControlCommon):
    @classmethod
    @freeze_time("2001-02-01")
    def setUpClass(cls):
        super().setUpClass()
        # Create sample ready to use Budget Control
        cls.budget_control = cls.BudgetControl.create(
            {
                "name": "CostCenter1/%s" % cls.year,
                "template_id": cls.budget_period.template_id.id,
                "budget_period_id": cls.budget_period.id,
                "analytic_account_id": cls.costcenter1.id,
                "plan_date_range_type_id": cls.date_range_type.id,
                "template_line_ids": [
                    cls.template_line1.id,
                    cls.template_line2.id,
                    cls.template_line3.id,
                ],
            }
        )
        # Test item created for 3 kpi x 4 quarters = 12 budget items
        cls.budget_control.prepare_budget_control_matrix()
        assert len(cls.budget_control.line_ids) == 12
        # Assign budget.control amount: KPI1 = 100x4=400, KPI2=800, KPI3=1,200
        cls.budget_control.line_ids.filtered(lambda x: x.kpi_id == cls.kpi1).write(
            {"amount": 100}
        )
        cls.budget_control.line_ids.filtered(lambda x: x.kpi_id == cls.kpi2).write(
            {"amount": 200}
        )
        cls.budget_control.line_ids.filtered(lambda x: x.kpi_id == cls.kpi3).write(
            {"amount": 300}
        )

    @freeze_time("2001-02-01")
    def test_01_budget_control_revision(self):
        """Revision budget control, commitment should normal process"""
        self.assertTrue(self.budget_control.init_revision)
        self.assertEqual(self.budget_control.revision_number, 0)
        self.assertEqual(self.budget_control.amount_budget, 2400.0)
        # Check state not cancel (in tree view), not allow to revision
        self.assertEqual(self.budget_control.state, "draft")
        with self.assertRaises(UserError):
            self.budget_control.action_create_revision()
        self.budget_control.action_cancel()
        self.assertEqual(self.budget_control.state, "cancel")
        revision_val = self.budget_control.action_create_revision()
        domain_list = ast.literal_eval(revision_val["domain"])
        # Check new revision should have next number and init revision is false
        new_budget_control = self.BudgetControl.browse(domain_list[0][2])
        self.assertFalse(self.budget_control.active)
        self.assertFalse(new_budget_control.init_revision)
        self.assertEqual(new_budget_control.revision_number, 1)
        self.assertEqual(self.budget_control.amount_budget, 0.0)
        self.assertEqual(new_budget_control.amount_budget, 2400.0)

        # Check budget must commit with newest budget always.
        bill1 = self._create_simple_bill(self.costcenter1, self.account_kpi1, 400)
        # Allocate and control budget
        self.budget_period.control_budget = True
        new_budget_control.allocated_amount = 2400
        new_budget_control.action_done()
        bill1.action_post()
        self.assertTrue(bill1.budget_move_ids)
        # trigger check amount budget
        new_budget_control._compute_budget_info()
        self.assertEqual(new_budget_control.amount_balance, 2000.0)
