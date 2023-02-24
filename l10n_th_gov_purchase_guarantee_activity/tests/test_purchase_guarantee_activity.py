# Copyright 2023 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo.tests.common import Form

from odoo.addons.l10n_th_gov_purchase_guarantee.tests.test_purchase_guarantee import (
    TestPurchaseGuarantee,
)


class TestPurchaseGuaranteeActivity(TestPurchaseGuarantee):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        budget_activity_obj = cls.env["budget.activity"]  # Create sample activity
        account_obj = cls.env["account.account"]
        cls.account_recv = account_obj.create(
            {
                "code": "TEST0001",
                "name": "Debtors - (test)",
                "reconcile": True,
                "user_type_id": cls.env.ref("account.data_account_type_receivable").id,
            }
        )
        cls.activity1 = budget_activity_obj.create(
            {
                "name": "Activity 1",
                "account_id": cls.account_recv.id,
            }
        )

    def test_01_change_activity(self):
        """Test onchange activity, account should be change to account in activity"""
        self.assertEqual(
            self.guarantee_bid_guarantee.account_id, self.account_guarantee
        )
        self.assertFalse(self.guarantee_bid_guarantee.activity_id)
        with Form(self.guarantee_bid_guarantee) as method:
            method.activity_id = self.activity1
        self.assertEqual(self.guarantee_bid_guarantee.account_id, self.account_recv)
        self.assertEqual(self.guarantee_bid_guarantee.activity_id, self.activity1)
