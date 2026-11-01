# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, new_test_user


class TestBudgetPeriod(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.BudgetPeriod = cls.env["budget.period"]
        cls.company = cls.env.company
        cls.branch = cls.env["res.company"].create(
            {"name": "Test Branch", "parent_id": cls.company.id}
        )
        cls.other_company = cls.env["res.company"].create(
            {"name": "Test Other Company"}
        )
        # Far years keep the tests apart from periods of other modules
        cls.period = cls._create_period(cls, "FY2301", "2301-01-01", "2301-12-31")

    def _create_period(self, name, date_from, date_to, companies=None):
        vals = {
            "name": name,
            "bm_date_from": date_from,
            "bm_date_to": date_to,
        }
        if companies:
            vals["company_ids"] = [Command.set(companies.ids)]
        return self.BudgetPeriod.create(vals)

    def test_01_period_dates(self):
        with self.assertRaisesRegex(ValidationError, "start date must be before"):
            self._create_period("Wrong", "2302-12-31", "2302-01-01")

    def test_02_fiscal_period_overlap(self):
        # Overlaps a period of all companies
        with self.assertRaisesRegex(ValidationError, "overlaps"):
            self._create_period(
                "FY2301 Branch", "2301-06-01", "2302-05-31", self.branch
            )
        # Company periods: sibling companies may overlap, the parent and its
        # branch may not
        company_period = self._create_period(
            "FY2302", "2302-01-01", "2302-12-31", self.company
        )
        other_period = self._create_period(
            "FY2302 Other", "2302-01-01", "2302-12-31", self.other_company
        )
        with self.assertRaisesRegex(ValidationError, "overlaps"):
            self._create_period(
                "FY2302 Branch", "2302-06-01", "2302-06-30", self.branch
            )
        with self.assertRaisesRegex(ValidationError, "overlaps"):
            other_period.company_ids = [Command.link(self.branch.id)]
        with self.assertRaisesRegex(ValidationError, "overlaps"):
            self._create_period("FY2302 All", "2302-12-31", "2303-12-30")
        # Adjacent periods do not overlap
        next_period = self._create_period(
            "FY2303", "2303-01-01", "2303-12-31", self.company
        )
        self.assertTrue(company_period | next_period)

    def test_03_get_fiscal_period(self):
        self.assertEqual(
            self.BudgetPeriod._get_fiscal_period("2301-05-15"), self.period
        )
        self.assertFalse(self.BudgetPeriod._get_fiscal_period("2304-05-15"))
        company_period = self._create_period(
            "FY2302", "2302-01-01", "2302-12-31", self.company
        )
        # A branch takes the period of its parent company
        self.assertEqual(
            self.BudgetPeriod._get_fiscal_period("2302-05-15", self.branch),
            company_period,
        )
        self.assertFalse(
            self.BudgetPeriod._get_fiscal_period("2302-05-15", self.other_company)
        )

    def test_04_archived_branch_overlap(self):
        branch_period = self._create_period(
            "FY2302 Branch", "2302-01-01", "2302-12-31", self.branch
        )
        self.branch.active = False
        with self.assertRaisesRegex(ValidationError, "overlaps"):
            self._create_period("FY2302", "2302-01-01", "2302-12-31", self.company)
        self.assertTrue(branch_period)

    def test_05_access(self):
        company_period = self._create_period(
            "FY2302", "2302-01-01", "2302-12-31", self.company
        )
        other_period = self._create_period(
            "FY2302 Other", "2302-01-01", "2302-12-31", self.other_company
        )
        user = new_test_user(
            self.env,
            login="test_base_budget_user",
            company_id=self.branch.id,
            company_ids=[Command.set(self.branch.ids)],
        )
        Period = self.BudgetPeriod.with_user(user)
        # A branch sees the periods of all companies and of its parent company
        self.assertEqual(
            Period.search([("id", "in", (company_period | other_period).ids)]),
            company_period,
        )
        self.assertEqual(Period.browse(self.period.id).name, "FY2301")
        with self.assertRaises(AccessError):
            Period.create(
                {
                    "name": "FY2303",
                    "bm_date_from": "2303-01-01",
                    "bm_date_to": "2303-12-31",
                }
            )
        admin = new_test_user(
            self.env, login="test_base_budget_admin", groups="base.group_system"
        )
        period = self.BudgetPeriod.with_user(admin).create(
            {
                "name": "FY2303",
                "bm_date_from": "2303-01-01",
                "bm_date_to": "2303-12-31",
            }
        )
        period.name = "FY2303 Admin"
        period.unlink()
