# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.stock_analytic.tests.test_stock_picking import TestStockPicking
from odoo.addons.stock_analytic.tests.test_stock_scrap import TestStockScrap


class TestStockBudgetAllocation(TestStockScrap, TestStockPicking):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
