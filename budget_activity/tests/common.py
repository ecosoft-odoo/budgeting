# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from freezegun import freeze_time

from odoo.addons.budget_control.tests.common import BudgetControlCommon


class BudgetActivityCommon(BudgetControlCommon):
    @classmethod
    @freeze_time("2001-02-01")
    def setUpClass(cls):
        super().setUpClass()
        BudgetActivity = cls.env["budget.activity"]  # Create sample activity
        cls.activity1 = BudgetActivity.create(
            {"name": "Activity 1", "account_id": cls.account_kpi1.id}
        )
        cls.activity2 = BudgetActivity.create(
            {"name": "Activity 2", "account_id": cls.account_kpi2.id}
        )
