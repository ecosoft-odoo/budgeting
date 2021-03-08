# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import common


class TestBudgetControlTierValidation(common.TransactionCase):
    def setUp(self):
        super(TestBudgetControlTierValidation, self).setUp()

        # common models
        self.budget_control = self.env["budget.control"]
        self.tier_definition = self.env["tier.definition"]

    def test_get_under_validation_exceptions(self):
        self.assertIn(
            "route_id", self.budget_control._get_under_validation_exceptions()
        )

    def test_get_tier_validation_model_names(self):
        self.assertIn(
            "budget.control",
            self.tier_definition._get_tier_validation_model_names(),
        )
