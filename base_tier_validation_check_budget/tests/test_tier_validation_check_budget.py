# Copyright 2020 Ecosoft (http://ecosoft.co.th)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo.tests import tagged

from odoo.addons.base_tier_validation.tests.common import CommonTierValidation


@tagged("post_install", "-at_install")
class TierTierValidationCheckBudget(CommonTierValidation):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from .tier_validation_tester import TierValidationTester

        cls.loader.update_registry((TierValidationTester,))

    def test_01_request_validation_check_budget_no_budget(self):
        self.tier_definition.check_budget = True
        self.assertFalse(self.test_record.review_ids)
        reviews = self.test_record.with_user(self.test_user_2.id).request_validation()
        self.assertTrue(reviews)
        record = self.test_record.with_user(self.test_user_1.id)
        record.invalidate_model()
        record.validate_tier()
        self.assertTrue(record.validated)
