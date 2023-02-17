# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo.tests import tagged

from odoo.addons.account_asset_management.tests.test_account_asset_management import (
    TestAssetManagement,
)


@tagged("post_install", "-at_install")
class TestAssetNumber(TestAssetManagement):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_01_asset_move_budget(self):
        """Check asset is default not_affect_budget"""
        res = super().test_01_nonprorata_basic()
        asset = self.asset_model.search([], limit=1)
        self.assertTrue(asset.not_affect_budget)
        return res
