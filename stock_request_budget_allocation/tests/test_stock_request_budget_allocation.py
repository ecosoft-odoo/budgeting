# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import tagged

from odoo.addons.stock_request_analytic.tests.test_stock_request_analytic import (
    TestStockRequestAnalytic,
)


@tagged("post_install", "-at_install")
class TestStockRequestBudgetAllocation(TestStockRequestAnalytic):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
