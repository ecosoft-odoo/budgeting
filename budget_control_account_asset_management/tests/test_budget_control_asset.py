# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import time

from odoo import Command
from odoo.tests import tagged

from odoo.addons.account_asset_management.tests.test_account_asset_management import (
    TestAssetManagement,
)
from odoo.addons.budget_control.tests.common import get_budget_common_class


@tagged("post_install", "-at_install")
class TestAssetNumber(TestAssetManagement, get_budget_common_class()):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create budget plan with 1 analytic
        lines = [
            Command.create(
                {"analytic_account_id": cls.costcenter1.id, "amount": 2400.0}
            )
        ]
        cls.budget_plan = cls.create_budget_plan(
            cls,
            name="Test - Plan {cls.budget_period.name}",
            budget_period=cls.budget_period,
            lines=lines,
        )
        cls.budget_plan.action_confirm()
        cls.budget_plan.action_create_update_budget_control()
        cls.budget_plan.action_done()

        # Refresh data
        cls.budget_plan.invalidate_recordset()

        cls.budget_control = cls.budget_plan.budget_control_ids
        cls.budget_control.template_line_ids = [
            cls.template_line1.id,
            cls.template_line2.id,
            cls.template_line3.id,
        ]

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

        # Add account expense depreciation to budget template
        cls.template_line1.write(
            {"account_ids": [4, cls.ict3Y.account_expense_depreciation_id.id]}
        )

    def test_01_asset_move_budget(self):
        """Check asset is affect budget"""
        self.assertTrue(self.env.company.asset_not_affect_budget)

        # Test affect budget
        self.env.company.asset_not_affect_budget = False
        analytic_distribution = {self.costcenter1.id: 100}
        ict0 = self.asset_model.create(
            {
                "method_time": "year",
                "method_number": 3,
                "method_period": "year",
                "name": "Laptop",
                "code": "PI00101",
                "purchase_value": 3000.0,
                "profile_id": self.ict3Y.id,
                "date_start": time.strftime("%Y-01-01"),
                "analytic_distribution": analytic_distribution,
            }
        )
        self.assertFalse(ict0.not_affect_budget)

        # compute the depreciation boards
        ict0.compute_depreciation_board()
        ict0.invalidate_recordset()

        self.assertAlmostEqual(self.budget_control.amount_budget, 2400.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 2400.0)
        # post the first depreciation line
        ict0.validate()
        ict0.depreciation_line_ids[1].create_move()
        original_move = ict0.depreciation_line_ids[1].move_id
        ict0.invalidate_recordset()

        # Budget commit created
        self.assertTrue(original_move.budget_move_ids)
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_budget, 2400.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 1000.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 1400.0)

    def test_02_asset_move_not_affect_budget(self):
        """Check asset is not affect budget"""
        self.assertTrue(self.env.company.asset_not_affect_budget)

        analytic_distribution = {self.costcenter1.id: 100}
        ict0 = self.asset_model.create(
            {
                "method_time": "year",
                "method_number": 3,
                "method_period": "year",
                "name": "Laptop",
                "code": "PI00101",
                "purchase_value": 3000.0,
                "profile_id": self.ict3Y.id,
                "date_start": time.strftime("%Y-01-01"),
                "analytic_distribution": analytic_distribution,
            }
        )
        self.assertTrue(ict0.not_affect_budget)

        # compute the depreciation boards
        ict0.compute_depreciation_board()
        ict0.invalidate_recordset()

        self.assertAlmostEqual(self.budget_control.amount_budget, 2400.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 2400.0)
        # post the first depreciation line
        ict0.validate()
        ict0.depreciation_line_ids[1].create_move()
        original_move = ict0.depreciation_line_ids[1].move_id
        ict0.invalidate_recordset()

        # Budget commit created
        self.assertFalse(original_move.budget_move_ids)
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_budget, 2400.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 2400.0)
