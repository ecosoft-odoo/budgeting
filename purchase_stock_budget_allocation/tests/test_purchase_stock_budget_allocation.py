# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.purchase_stock_analytic.tests.test_purchase_stock_analytic import (
    TestPurchaseStockAnalytic,
)


class TestPurchaseStockBudgetAllocation(TestPurchaseStockAnalytic):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
