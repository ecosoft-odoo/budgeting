# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from freezegun import freeze_time

from odoo.tests import tagged
from odoo.tests.common import Form

from odoo.addons.budget_allocation.tests.test_budget_allocation import (
    TestBudgetAllocation,
)


@tagged("post_install", "-at_install")
class TestAssetTransferAllocation(TestBudgetAllocation):
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
        cls.misc_transfer_journal = cls.env["account.journal"].create(
            {
                "name": "Misc Transfer Journal - (test)",
                "code": "MiscT-Test",
                "type": "general",
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
        # Profile Under Construction
        cls.profile_auc = cls.asset_profile_model.create(
            {
                "account_expense_depreciation_id": cls.account_expense.id,
                "account_asset_id": cls.account_asset.id,
                "account_depreciation_id": cls.account_asset.id,
                "journal_id": cls.purchase_journal.id,
                "transfer_journal_id": cls.misc_transfer_journal.id,
                "asset_product_item": True,
                "name": "Asset Under Construction",
                "method_time": "year",
                "method_number": 0,
                "method_period": "year",
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
        asset_auc = self.asset_model.create(
            {
                "name": "test asset",
                "profile_id": self.profile_auc.id,
                "purchase_value": 1500,
                "date_start": "1901-02-01",
                "method_time": "year",
                "method_number": 0,
                "method_period": "year",
            }
        )
        # Add analytic in asset, it should default fund1
        with Form(asset_auc) as a:
            a.account_analytic_id = self.costcenterX
        self.assertEqual(asset_auc.account_analytic_id, self.costcenterX)
        self.assertEqual(
            asset_auc.fund_id, asset_auc.account_analytic_id.allocation_line_ids.fund_id
        )
        asset_auc.validate()
        # Create Asset Transfer
        transfer_form = Form(
            self.env["account.asset.transfer"].with_context(active_ids=asset_auc.ids)
        )
        transfer_wiz = transfer_form.save()
        with transfer_form.to_asset_ids.new() as to_asset:
            to_asset.asset_name = "Asset 1"
            to_asset.asset_profile_id = self.car5y
            to_asset.quantity = 1
            to_asset.price_unit = 1500
        transfer_form.save()
        # Check fund line in asset transfer will default following asset auc
        self.assertEqual(transfer_wiz.to_asset_ids.fund_id, asset_auc.fund_id)
        res = transfer_wiz.transfer()
        transfer_move = self.env["account.move"].browse(res["domain"][0][2])
        assets = transfer_move.invoice_line_ids.mapped("asset_id")
        # 2 new assets created, and value equal to original assets
        new_assets = assets.filtered(lambda l: l.state == "draft")
        self.assertEqual(sum(new_assets.mapped("purchase_value")), 1500.0)
        self.assertEqual(new_assets.mapped("fund_id"), asset_auc.fund_id)
        self.assertTrue(new_assets.mapped("not_affect_budget"))
