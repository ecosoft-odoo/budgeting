# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from freezegun import freeze_time

from odoo.tests import tagged

from odoo.addons.budget_control_purchase.tests.test_budget_purchase import (
    TestBudgetControlPurchase,
)


@tagged("post_install", "-at_install")
class TestBudgetControlPurchaseAgreement(TestBudgetControlPurchase):
    @classmethod
    @freeze_time("2001-02-01")
    def setUpClass(cls):
        super().setUpClass()
