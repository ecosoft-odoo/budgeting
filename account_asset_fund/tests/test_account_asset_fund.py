# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from freezegun import freeze_time

from odoo.tests import tagged
from odoo.tests.common import Form

from odoo.addons.budget_allocation.tests.test_budget_allocation import (
    TestBudgetAllocation,
)


@tagged("post_install", "-at_install")
class TestAccountAssetFund(TestBudgetAllocation):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.account_model = cls.env["account.account"]
        cls.asset_model = cls.env["account.asset"]
        cls.asset_profile_model = cls.env["account.asset.profile"]
        # Create expense account
        account_type_expense = cls.env.ref("account.data_account_type_expenses")
        cls.account_expense = cls.account_model.create(
            {
                "code": "TEST99999-Expense",
                "name": "Account - Test Expense",
                "user_type_id": account_type_expense.id,
            }
        )
        # Create asset account
        account_type_asset = cls.env.ref("account.data_account_type_current_assets")
        cls.account_asset = cls.account_model.create(
            {
                "code": "TEST99999-Asset",
                "name": "Account - Test Asset",
                "user_type_id": account_type_asset.id,
            }
        )
        # Create Journal Purchase
        cls.purchase_journal = cls.env["account.journal"].create(
            {
                "name": "Purchase Journal - (test)",
                "code": "TEST-P",
                "type": "purchase",
            }
        )
        cls.car5y = cls.asset_profile_model.create(
            {
                "account_expense_depreciation_id": cls.account_expense.id,
                "account_asset_id": cls.account_asset.id,
                "account_depreciation_id": cls.account_asset.id,
                "journal_id": cls.purchase_journal.id,
                "name": "Cars - 5 Years",
                "method_time": "year",
                "method_number": 5,
                "method_period": "month",
            }
        )

    @freeze_time("2001-02-01")
    def test_01_commitment_asset_fund(self):
        """Create same analytic, difference fund, difference analytic tags
        line 1: Costcenter1, Fund1, Tag1, 50.0
        line 2: Costcenter1, Fund1, Tag2, 100.0
        line 3: Costcenter1, Fund2,     , 100.0
        line 4: CostcenterX, Fund1,     , 100.0
        """
        # budget control is depends on budget allocation
        budget_control_ids = self.test_02_process_budget_allocation()
        # Test with 1 budget control, it can commit budget not over 250
        budget_control = budget_control_ids[0]
        self.assertEqual(
            sum(budget_control.allocation_line_ids.mapped("allocated_amount")), 250
        )
        budget_control.write({"template_line_ids": [self.template_line1.id]})
        # Test item created for 1 kpi x 4 quarters = 4 budget items
        budget_control.prepare_budget_control_matrix()
        assert len(budget_control.line_ids) == 4
        # Assign budget.control amount: 250
        with Form(budget_control.line_ids[0]) as line:
            line.amount = 250
        # Control budget
        budget_control.action_done()
        self.budget_period.control_budget = True
        # Create asset
        asset = self.asset_model.create(
            {
                "name": "test asset",
                "profile_id": self.car5y.id,
                "purchase_value": 1500,
                "date_start": "1901-02-01",
                "method_time": "year",
                "method_number": 3,
                "method_period": "month",
            }
        )
        # Add analytic in asset, it should default fund1
        with Form(asset) as a:
            a.account_analytic_id = self.costcenterX
        self.assertEqual(asset.account_analytic_id, self.costcenterX)
        self.assertEqual(
            asset.fund_id, asset.account_analytic_id.allocation_line_ids.fund_id
        )

        asset.compute_depreciation_board()
        asset.refresh()
        # check values in the depreciation board
        move_id = asset.depreciation_line_ids[1].create_move()
        move = self.env["account.move"].browse(move_id)
        self.assertEqual(move.line_ids.mapped("fund_id"), asset.fund_id)
