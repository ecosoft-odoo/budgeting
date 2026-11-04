# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from psycopg2 import IntegrityError

from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, tagged
from odoo.tests.common import new_test_user
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestBudgetActivity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Activity = cls.env["budget.activity"]
        cls.Keyword = cls.env["budget.activity.keyword"]
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create({"name": "Other Company"})
        cls.activity = cls.Activity.create({"name": "Base Activity"})
        cls.user = new_test_user(cls.env, login="activity_user")
        cls.manager = new_test_user(
            cls.env,
            login="activity_manager",
            groups="base.group_user,base_budget_activity.group_budget_activity_manager",
        )

    @mute_logger("odoo.sql_db")
    def test_01_activity_name_is_unique(self):
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self.Activity.create({"name": self.activity.name})

    @mute_logger("odoo.sql_db")
    def test_02_keyword_name_is_unique_per_company(self):
        self.Keyword.create({"name": "Travel", "company_id": self.company.id})
        self.Keyword.create({"name": "Travel", "company_id": self.other_company.id})
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self.Keyword.create({"name": "Travel", "company_id": self.company.id})

    def test_03_search_by_keyword(self):
        keyword = self.Keyword.create({"name": "Seminar"})
        self.activity.keyword_ids = keyword
        found = self.Activity.name_search("Seminar")
        self.assertIn(self.activity.id, [res[0] for res in found])

    def test_04_keyword_of_other_company(self):
        keyword = self.Keyword.create(
            {"name": "Other", "company_id": self.other_company.id}
        )
        with self.assertRaises(UserError):
            self.activity.keyword_ids = keyword

    def test_05_company_rule(self):
        other = self.Activity.create(
            {"name": "Other Activity", "company_id": self.other_company.id}
        )
        shared = self.Activity.create({"name": "Shared Activity", "company_id": False})
        other_keyword = self.Keyword.create(
            {"name": "Other", "company_id": self.other_company.id}
        )
        Activity = self.Activity.with_user(self.manager)
        self.assertFalse(Activity.search_count([("id", "=", other.id)]))
        self.assertTrue(Activity.search_count([("id", "=", shared.id)]))
        self.assertTrue(Activity.search_count([("id", "=", self.activity.id)]))
        Keyword = self.Keyword.with_user(self.manager)
        self.assertFalse(Keyword.search_count([("id", "=", other_keyword.id)]))

    def test_06_access_rights(self):
        self.assertEqual(self.activity.with_user(self.user).name, "Base Activity")
        for operation in (
            lambda: self.activity.with_user(self.user).write({"name": "Forbidden"}),
            lambda: self.Activity.with_user(self.user).create({"name": "Forbidden"}),
            lambda: self.Keyword.with_user(self.user).create({"name": "Forbidden"}),
        ):
            with self.assertRaises(AccessError), self.cr.savepoint():
                operation()
        activity = self.Activity.with_user(self.manager).create({"name": "By Manager"})
        activity.write({"name": "Renamed"})
        activity.action_archive()
        activity.unlink()
