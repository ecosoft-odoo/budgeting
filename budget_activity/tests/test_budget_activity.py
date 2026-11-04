# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from freezegun import freeze_time
from psycopg2 import IntegrityError

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import Form, tagged
from odoo.tools import mute_logger

from odoo.addons.budget_control.tests.common import get_budget_common_class


@tagged("post_install", "-at_install")
class TestBudgetActivity(get_budget_common_class()):
    @classmethod
    @freeze_time("2001-02-01")
    def setUpClass(cls):
        super().setUpClass()
        BudgetActivity = cls.env["budget.activity"]  # Create sample activity
        cls.env.company.budget_control_key = "activity_id"  # Control by activity
        cls.activity1 = BudgetActivity.create(
            {
                "name": "Activity 1",
                "kpi_id": cls.kpi1.id,
                "account_id": cls.account_kpi1.id,
            }
        )
        cls.activity2 = BudgetActivity.create(
            {
                "name": "Activity 2",
                "kpi_id": cls.kpi2.id,
                "account_id": cls.account_kpi2.id,
            }
        )
        cls.activity3 = BudgetActivity.create(
            {
                "name": "Activity 3",
                "kpi_id": cls.kpi3.id,
                "account_id": cls.account_kpi3.id,
            }
        )
        # Add activity on template line
        with Form(cls.template_line1) as line:
            line.kpi_id = cls.kpi1
        with Form(cls.template_line2) as line:
            line.kpi_id = cls.kpi2
        with Form(cls.template_line3) as line:
            line.kpi_id = cls.kpi3

        cls.budget_control = cls.create_budget_control(cls, cls.costcenter1, 2400.0)
        # Test item created for 3 kpi x 4 quarters = 12 budget items
        assert len(cls.budget_control.line_ids) == 12
        # Assign budget.control amount: KPI1 = 100x4=400, KPI2=800, KPI3=1,200
        cls.budget_control.line_ids.filtered(lambda x: x.kpi_id == cls.kpi1).write(
            {"amount": 100}
        )
        cls.budget_control.line_ids.filtered(lambda x: x.kpi_id == cls.kpi2).write(
            {"amount": 200}
        )
        cls.budget_control.line_ids.filtered(lambda x: x.kpi_id == cls.kpi3).write(
            {"amount": 300}
        )

        # Control budget
        cls.budget_period.control_budget = True
        cls.budget_control.action_submit()
        cls.budget_control.action_done()

    def _create_simple_bill_activity(
        self, analytic_distribution, activity, amount, product=None
    ):
        invoice = self.Move.create(
            {
                "move_type": "in_invoice",
                "partner_id": self.vendor.id,
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "quantity": 1,
                            "product_id": product.id if product else False,
                            "activity_id": activity.id,
                            "price_unit": amount,
                            "analytic_distribution": analytic_distribution,
                        },
                    )
                ],
            }
        )
        return invoice

    def _get_monitor_actual(self, move_line):
        self.env.flush_all()
        return self.env["budget.monitor.report"].search(
            [
                ("res_id", "=", f"account.move.line,{move_line.id}"),
                ("amount_type", "=", "80_actual"),
            ]
        )

    @freeze_time("2001-02-01")
    def test_01_budget_activity_account(self):
        """
        On vendor bill,
        - If no activity, budget follows product's account
        - If activity is selected, account follows activity's regardless of product
        - User can always change account code afterwards
        - Posting invoice, will create budget move with activity
        """
        analytic_distribution = {self.costcenter1.id: 100}
        price_unit = 10.0

        bill1 = self._create_simple_bill_activity(
            analytic_distribution, self.activity1, price_unit
        )
        self.assertEqual(
            self.activity1.account_id, bill1.invoice_line_ids[0].account_id
        )
        # Change to product2, account should not change.
        with (
            Form(bill1) as invoice_form,
            invoice_form.invoice_line_ids.edit(0) as line_form,
        ):
            line_form.product_id = self.product2
            line_form.price_unit = price_unit  # Change product, amount will reset
        self.assertEqual(
            self.activity1.account_id, bill1.invoice_line_ids[0].account_id
        )
        self.assertEqual(self.product2, bill1.invoice_line_ids[0].product_id)
        self.assertEqual(self.activity1, bill1.invoice_line_ids[0].activity_id)

        # Change activity on template line for test no activity in template line
        # It should errors `not valid in template`
        with Form(self.template_line1) as line:
            line.kpi_id = self.kpi2
        with self.assertRaisesRegex(UserError, "not valid in template"):
            bill1.action_post()

        # Change activity on template line for test multi activity in template line
        with Form(self.template_line1) as line:
            line.kpi_id = self.kpi1
        with Form(self.template_line2) as line:
            line.kpi_id = self.kpi1
        with self.assertRaisesRegex(
            UserError,
            "Template Lines has more than one KPI being referenced by the same",
        ):
            bill1.action_post()

        # Change back to basic
        with Form(self.template_line2) as line:
            line.kpi_id = self.kpi2
        # The failed posts left the bill in draft, set account = account in activity
        bill1.invoice_line_ids[0].account_id = self.activity1.account_id
        # All values will be passed to budget move
        bill1.action_post()
        bill_line = bill1.invoice_line_ids[0]
        self.assertEqual(self.account_kpi1, bill1.budget_move_ids[0].account_id)
        self.assertEqual(self.product2, bill1.budget_move_ids[0].product_id)
        self.assertEqual(self.activity1, bill1.budget_move_ids[0].activity_id)
        self.assertEqual(self.kpi1, bill1.budget_move_ids[0].kpi_id)
        self.assertEqual(bill_line.analytic_line_ids.activity_id, self.activity1)
        self.assertEqual(
            self._get_monitor_actual(bill_line).activity_id, self.activity1
        )
        self.assertEqual(self.budget_control.amount_balance, 2390.0)

        # Check budget move must account equal accuont in activity
        with self.assertRaisesRegex(
            UserError, "Account not equal to Activity's Account"
        ):
            bill1.budget_move_ids[0].account_id = self.account_kpi3.id

        # Check change account in activity, after commit. it should not allow
        with (
            self.assertRaisesRegex(
                UserError,
                "You cannot change the account because it is already used in a commit.",
            ),
            Form(self.activity1) as activity,
        ):
            activity.account_id = self.account_kpi2
        # Same by ORM, removing the account too
        for account in (self.account_kpi2, self.Account):
            with self.assertRaisesRegex(UserError, "already used in a commit"):
                self.activity1.account_id = account
        # Other fields and unused activities can still change
        self.activity1.name = "Activity 1 (renamed)"
        self.activity3.account_id = self.account_kpiX
        self.assertEqual(self.activity3.account_id, self.account_kpiX)
        # An activity used by budget moves or templates cannot be deleted
        with (
            self.assertRaises(IntegrityError),
            self.cr.savepoint(),
            mute_logger("odoo.sql_db"),
        ):
            self.activity1.unlink()

    @freeze_time("2001-02-01")
    def test_02_budget_adjustment_activity(self):
        """
        On budget adjustment,
        - If no activity, budget follows product's account
        - If activity is selected, account follows activity's regardless of product
        - User can always change account code afterwards
        """
        self.assertEqual(self.budget_control.amount_balance, 2400.0)
        budget_adjust = self.BudgetAdjust.create(
            {
                "date_commit": "2001-02-01",
            }
        )
        with Form(budget_adjust.adjust_item_ids) as line:
            line.adjust_id = budget_adjust
            line.adjust_type = "consume"
            line.product_id = self.product1
            line.analytic_distribution = {self.costcenter1.id: 100}
            line.amount = 100.0
        adjust_line = line.save()
        self.assertEqual(adjust_line.account_id, self.account_kpi1)
        # Change to activity2, account should change to account_kpi2
        with Form(adjust_line) as line:
            line.activity_id = self.activity2
        self.assertEqual(adjust_line.account_id, self.activity2.account_id)
        # balance in budget control must be 'Decrease'
        budget_adjust.action_adjust()
        self.assertEqual(self.budget_control.amount_balance, 2300.0)
        self.assertEqual(adjust_line.budget_move_ids.activity_id, self.activity2)
        self.assertEqual(adjust_line.budget_move_ids.kpi_id, self.kpi2)

    @freeze_time("2001-02-01")
    def test_03_budget_activity_real_time_valuation(self):
        """
        On vendor bill of a product valued in real time,
        - The bill line keeps the stock valuation account of the product
        - The budget move takes the account of the activity, and its KPI
        """
        account_stock = self.Account.create(
            {"name": "Stock", "code": "STOCK", "account_type": "asset_current"}
        )
        category = self.env["product.category"].create(
            {
                "name": "Real Time",
                "property_valuation": "real_time",
                "property_stock_valuation_account_id": account_stock.id,
            }
        )
        self.product1.write({"is_storable": True, "categ_id": category.id})
        self.assertEqual(self.product1.valuation, "real_time")

        bill = self._create_simple_bill_activity(
            {self.costcenter1.id: 100}, self.activity2, 10.0, product=self.product1
        )
        bill_line = bill.invoice_line_ids
        self.assertEqual(bill_line.account_id, account_stock)
        bill.action_post()
        self.assertEqual(bill.budget_move_ids.account_id, self.account_kpi2)
        self.assertEqual(bill.budget_move_ids.activity_id, self.activity2)
        self.assertEqual(bill.budget_move_ids.kpi_id, self.kpi2)
        self.assertEqual(self.budget_control.amount_balance, 2390.0)

    @freeze_time("2001-02-01")
    def test_04_budget_control_by_account(self):
        """
        Budget controlled by account, with activities installed,
        - Activity is not required, the budget move follows the line's account
        - A line with activity keeps the account chosen by the user
        """
        self.env.company.budget_control_key = "account_id"
        bill = self._create_simple_bill(
            {self.costcenter1.id: 100}, self.account_kpi3, 10.0
        )
        self.assertFalse(bill.invoice_line_ids.required_activity)
        bill.action_post()
        self.assertEqual(bill.budget_move_ids.account_id, self.account_kpi3)
        self.assertFalse(bill.budget_move_ids.activity_id)
        self.assertEqual(bill.budget_move_ids.kpi_id, self.kpi3)

        bill2 = self._create_simple_bill_activity(
            {self.costcenter1.id: 100}, self.activity1, 10.0
        )
        bill2.invoice_line_ids.account_id = self.account_kpi2
        bill2.action_post()
        self.assertEqual(bill2.budget_move_ids.account_id, self.account_kpi2)
        self.assertEqual(bill2.budget_move_ids.activity_id, self.activity1)
        self.assertEqual(bill2.budget_move_ids.kpi_id, self.kpi2)

    @freeze_time("2001-02-01")
    def test_05_budget_activity_required(self):
        """
        Budget controlled by activity, a vendor bill line commits budget only
        with an activity of its company or shared, mapped to an account
        """
        analytic_distribution = {self.costcenter1.id: 100}
        bill = self._create_simple_bill(analytic_distribution, self.account_kpi1, 10.0)
        self.assertTrue(bill.invoice_line_ids.required_activity)
        with self.assertRaisesRegex(UserError, "Please select an activity"):
            bill.action_post()
        # Activity of another company
        activity_b = self.env["budget.activity"].create(
            {
                "name": "Activity B",
                "kpi_id": self.kpi1.id,
                "company_id": self.company_b.id,
            }
        )
        bill.invoice_line_ids.activity_id = activity_b
        with self.assertRaisesRegex(UserError, "is not allowed to use the activity"):
            bill.action_post()
        # Activity without account, shared by all companies
        activity = self.env["budget.activity"].create(
            {
                "name": "Activity without account",
                "kpi_id": self.kpi1.id,
                "company_id": False,
            }
        )
        bill.invoice_line_ids.write(
            {"activity_id": activity.id, "account_id": self.account_kpi1.id}
        )
        with self.assertRaisesRegex(UserError, "Please set the account"):
            bill.action_post()
        activity.account_id = self.account_kpi1
        self.template_line1.budget_activity_ids |= activity
        bill.action_post()
        self.assertEqual(bill.budget_move_ids.activity_id, activity)
        self.assertEqual(bill.budget_move_ids.kpi_id, self.kpi1)
        # Lines on a bypassed account need no activity
        self.account_kpiX.budget_bypass = True
        bill2 = self._create_simple_bill(analytic_distribution, self.account_kpiX, 10.0)
        # but an activity, which gives its account, is still checked
        bill2.invoice_line_ids.write(
            {"activity_id": activity_b.id, "account_id": self.account_kpiX.id}
        )
        with self.assertRaisesRegex(UserError, "is not allowed to use the activity"):
            bill2.action_post()
        bill2.invoice_line_ids.activity_id = False
        bill2.action_post()
        self.assertEqual(bill2.state, "posted")

    @freeze_time("2001-02-01")
    def test_06_budget_check_by_activity(self):
        """
        Budget controlled by activity, at the level of analytic & KPI,
        - The activity gives the KPI checked, not the account of the product
        - Activity 1 (KPI 1, budget 400) cannot consume 401
        - Activity 2 (KPI 2, budget 800) can
        """
        self.budget_period.control_level = "analytic_kpi"
        analytic_distribution = {self.costcenter1.id: 100}
        # Product 2 books the account of KPI 2, Activity 1 maps to KPI 1
        bill1 = self._create_simple_bill_activity(
            analytic_distribution, self.activity1, 401.0, product=self.product2
        )
        with self.assertRaisesRegex(UserError, "Budget not sufficient") as error:
            bill1.action_post()
        self.assertIn(self.kpi1.name, str(error.exception))
        bill2 = self._create_simple_bill_activity(
            analytic_distribution, self.activity2, 401.0, product=self.product2
        )
        bill2.action_post()
        self.assertEqual(bill2.budget_move_ids.kpi_id, self.kpi2)
        self.assertEqual(self.budget_control.amount_balance, 1999.0)
