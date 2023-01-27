# Copyright 2020 Ecosoft (http://ecosoft.co.th)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
from odoo_test_helper import FakeModelLoader

from odoo.tests import common
from odoo.tests.common import tagged


@tagged("post_install", "-at_install")
class TierTierValidation(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super(TierTierValidation, cls).setUpClass()

        cls.loader = FakeModelLoader(cls.env, cls.__module__)
        cls.loader.backup_registry()
        from .tier_validation_tester import (
            TierValidationLineTester,
            TierValidationTester,
        )

        cls.loader.update_registry((TierValidationTester, TierValidationLineTester))
        cls.test_model = cls.env[TierValidationTester._name]
        cls.tester_model = cls.env["ir.model"].search(
            [("model", "=", "tier.validation.tester")]
        )
        cls.tester_line_model = cls.env["ir.model"].search(
            [("model", "=", "tier.validation.line.tester")]
        )
        # Access record:
        cls.env["ir.model.access"].create(
            [
                {
                    "name": "access.tester",
                    "model_id": cls.tester_model.id,
                    "perm_read": 1,
                    "perm_write": 1,
                    "perm_create": 1,
                    "perm_unlink": 1,
                },
                {
                    "name": "access.tester.line",
                    "model_id": cls.tester_line_model.id,
                    "perm_read": 1,
                    "perm_write": 1,
                    "perm_create": 1,
                    "perm_unlink": 1,
                },
            ]
        )

        # Create users:
        cls.group_system = cls.env.ref("base.group_system")
        group_ids = cls.group_system.ids
        cls.test_user_1 = cls.env["res.users"].create(
            {"name": "John", "login": "test1", "groups_id": [(6, 0, group_ids)]}
        )
        cls.test_user_2 = cls.env["res.users"].create(
            {"name": "Mike", "login": "test2"}
        )
        cls.test_user_3 = cls.env["res.users"].create(
            {"name": "John Wick", "login": "test3", "groups_id": [(6, 0, group_ids)]}
        )

        # Create tier definitions:
        cls.tier_def_obj = cls.env["tier.definition"].create(
            {
                "model_id": cls.tester_model.id,
                "review_type": "individual",
                "reviewer_id": cls.test_user_1.id,
                "definition_domain": "[('test_field', '>', 1.0)]",
                "sequence": 30,
            }
        )

        cls.test_record = cls.test_model.create(
            {
                "test_field": 2.5,
            }
        )

    @classmethod
    def tearDownClass(cls):
        cls.loader.restore_registry()
        super().tearDownClass()

    def test_01_request_validation_check_budget(self):
        """User 2 request a validation and user 1 approves it."""
        self.tier_def_obj.check_budget = True
        self.assertFalse(self.test_record.review_ids)
        reviews = self.test_record.with_user(self.test_user_2.id).request_validation()
        self.assertTrue(reviews)
        record = self.test_record.with_user(self.test_user_1.id)
        record.invalidate_cache()
        record.validate_tier()
        self.assertTrue(record.validated)
