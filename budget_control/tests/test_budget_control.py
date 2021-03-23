# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import datetime

from freezegun import freeze_time

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import BudgetControlCommon


@tagged("post_install", "-at_install")
class TestBudgetControl(BudgetControlCommon):
    @freeze_time("2001-02-01")
    def test_01_no_budget_control_check(self):
        """Invoice with analytic that has no budget_control candidate,
        - If use KPIs not in control, no check in all case
        - Else if use a valid KPI
            - If control_all_analytic_accounts is checked -> Lock
            - If analytic in control_analytic_account_ids -> Lock
            - Else -> No Lock
        """
        self.budget_period.account = True
        # KPI not in control, allow posting
        bill1 = self._create_simple_bill(
            self.costcenterX, self.account_kpiX, 100000
        )
        bill1.action_post()
        self.assertTrue(bill1.budget_move_ids)
        # Valid KPI + control_all_analytic_accounts is checked
        self.budget_period.control_all_analytic_accounts = True
        bill2 = self._create_simple_bill(
            self.costcenterX, self.account_kpi1, 100000
        )
        with self.assertRaises(UserError):
            bill2.action_post()
        bill2.button_draft()
        # Valid KPI + analytic in control_analytic_account_ids
        self.budget_period.control_analytic_account_ids = self.costcenterX
        bill3 = self._create_simple_bill(
            self.costcenterX, self.account_kpi1, 100000
        )
        with self.assertRaises(UserError):
            bill3.action_post()
        bill3.button_draft()
        # Else, even valid KPI
        self.budget_period.control_all_analytic_accounts = False
        self.budget_period.control_analytic_account_ids = False
        bill4 = self._create_simple_bill(
            self.costcenterX, self.account_kpi1, 100000
        )
        bill4.action_post()
        self.assertTrue(bill1.budget_move_ids)

    @freeze_time("2001-02-01")
    def test_02_budget_control_not_confirmed(self):
        """
        - If budget_control for an analytic exists but not confirmed,
          invoice raise warning
        - If budget_control for is not set allocated amount,
          invoice raise warning
        """
        self.budget_period.account = True
        bill1 = self._create_simple_bill(
            self.costcenter1, self.account_kpi1, 400
        )
        # Now, budget_control is not yet set to Done, raise error when post invoice
        with self.assertRaises(UserError):
            bill1.action_post()
        self.assertEqual(bill1.state, "posted")
        bill1.button_draft()
        self.assertEqual(bill1.state, "draft")
        self.assertFalse(bill1.budget_move_ids)
        # As budget_control has not set allocated_amount, raise error when set Done
        with self.assertRaises(UserError):
            self.budget_control.action_done()
        # Allocate and Done
        self.budget_control.allocated_amount = 2400
        self.budget_control.action_done()
        self.assertEqual(self.budget_control.released_amount, 2400)
        self.assertEqual(self.budget_control.state, "done")
        # Post again
        bill1.action_post()
        self.assertEqual(bill1.state, "posted")

    @freeze_time("2001-02-01")
    def test_03_control_level_analytic_kpi(self):
        """
        Budget Period set control_level to "analytic_kpi", check at KPI level
        If amount exceed 400, lock budget
        """
        self.budget_period.account = True
        self.budget_period.control_level = "analytic_kpi"
        # Budget Controlled
        self.budget_control.allocated_amount = 2400
        self.budget_control.action_done()
        # Test with amount = 401
        bill1 = self._create_simple_bill(
            self.costcenter1, self.account_kpi1, 401
        )
        with self.assertRaises(UserError):
            bill1.action_post()

    @freeze_time("2001-02-01")
    def test_04_control_level_analytic(self):
        """
        Budget Period set control_level to "analytic", check at Analytic level
        If amount exceed 400, not lock budget and still has balance after that
        """
        self.budget_period.account = True
        self.budget_period.control_level = "analytic"
        # Budget Controlled
        self.budget_control.allocated_amount = 2400
        self.budget_control.action_done()
        # Test with amount = 2000
        bill1 = self._create_simple_bill(
            self.costcenter1, self.account_kpi1, 2000
        )
        bill1.action_post()
        self.assertEqual(bill1.state, "posted")
        self.assertTrue(self.budget_control.amount_balance)

    @freeze_time("2001-02-01")
    def test_05_no_account_budget_check(self):
        """If budget.period is not set to check budget, no budget check in all cases"""
        # No budget check
        self.budget_period.account = False
        # Budget Controlled
        self.budget_control.allocated_amount = 2400
        self.budget_control.action_done()
        # Create big amount invoice transaction > 2400
        bill1 = self._create_simple_bill(
            self.costcenter1, self.account_kpi1, 100000
        )
        bill1.action_post()

    @freeze_time("2001-02-01")
    def test_06_refund_no_budget_check(self):
        """For refund, always not checking"""
        # First, make budget actual to exceed budget first
        self.budget_period.account = False  # No budget check first
        self.budget_control.allocated_amount = 2400
        self.budget_control.action_done()
        self.assertEqual(self.budget_control.amount_balance, 2400)
        bill1 = self._create_simple_bill(
            self.costcenter1, self.account_kpi1, 100000
        )
        bill1.action_post()
        self.assertEqual(self.budget_control.amount_balance, -97600)
        # Check budget, for in_refund, force no budget check
        self.budget_period.account = True
        self.budget_control.action_draft()
        invoice = self._create_invoice(
            "in_refund",
            self.vendor,
            datetime.today(),
            self.costcenter1,
            [{"account": self.account_kpi1, "price_unit": 100}],
        )
        invoice.action_post()
        self.assertEqual(self.budget_control.amount_balance, -97500)

    @freeze_time("2001-02-01")
    def test_07_auto_date_commit(self):
        """
        - Budget move's date_commit should follow that specified in _doc_date_fields
        - If date_commit is not inline with analytic date range, adjust it automatically
        - Use the auto date_commit to create budget move
        - On cancel of document (unlink budget moves), date_commit is set to False
        """
        self.budget_period.account = False
        # First setup self.costcenterX valid date range and auto adjust
        self.costcenterX.bm_date_from = "2001-01-01"
        self.costcenterX.bm_date_to = "2001-12-31"
        self.costcenterX.auto_adjust_date_commit = True
        # date_commit should follow that in _doc_date_fields
        bill1 = self._create_simple_bill(
            self.costcenterX, self.account_kpiX, 10
        )
        self.assertIn(
            "move_id.date",
            self.env["account.move.line"]._doc_date_fields,
        )
        bill1.invoice_date = "2001-05-05"
        bill1.date = "2001-05-05"
        bill1.action_post()
        self.assertEqual(
            bill1.invoice_date, bill1.budget_move_ids.mapped("date")[0]
        )
        # If date is out of range, adjust automatically, to analytic date range
        bill2 = self._create_simple_bill(
            self.costcenterX, self.account_kpiX, 10
        )
        self.assertIn(
            "move_id.date",
            self.env["account.move.line"]._doc_date_fields,
        )
        bill2.invoice_date = "2002-05-05"
        bill2.date = "2002-05-05"
        bill2.action_post()
        self.assertEqual(
            self.costcenterX.bm_date_to,
            bill2.budget_move_ids.mapped("date")[0],
        )
        # On cancel of document, date_commit = False
        bill2.button_draft()
        self.assertFalse(bill2.invoice_line_ids.mapped("date_commit")[0])

    def test_08_manual_date_commit_check(self):
        """
        - If date_commit is not inline with analytic date range, show error
        """
        self.budget_period.account = False
        # First setup self.costcenterX valid date range and auto adjust
        self.costcenterX.bm_date_from = "2001-01-01"
        self.costcenterX.bm_date_to = "2001-12-31"
        self.costcenterX.auto_adjust_date_commit = True
        # Manual Date Commit
        bill1 = self._create_simple_bill(
            self.costcenterX, self.account_kpiX, 10
        )
        bill1.invoice_date = "2001-05-05"
        bill1.date = "2001-05-05"
        # Use manual date_commit = "2002-10-10" which is not in range.
        bill1.invoice_line_ids[0].date_commit = "2002-10-10"
        with self.assertRaises(UserError):
            bill1.action_post()

    @freeze_time("2001-02-01")
    def test_09_force_no_budget_checkt(self):
        """
        By passing context["force_no_budget_check"] = True, no check in all case
        """
        self.budget_period.account = True
        # Budget Controlled
        self.budget_control.allocated_amount = 2400
        self.budget_control.action_done()
        # Test with bit amount
        bill1 = self._create_simple_bill(
            self.costcenter1, self.account_kpi1, 100000
        )
        bill1.with_context(force_no_budget_check=True).action_post()

    def test_10_recompute_budget_move_date_commit(self):
        """
        - Date budget commit should be the same after recompute
        """
        self.budget_period.account = False
        self.costcenterX.auto_adjust_date_commit = True
        # Ma
        bill1 = self._create_simple_bill(
            self.costcenterX, self.account_kpiX, 10
        )
        bill1.invoice_date = "2002-10-10"
        bill1.date = "2002-10-10"
        # Use manual date_commit = "2002-10-10" which is not in range.
        bill1.invoice_line_ids[0].date_commit = "2002-10-10"
        bill1.action_post()
        self.assertEqual(
            bill1.budget_move_ids[0].date,
            bill1.invoice_line_ids[0].date_commit,
        )
        bill1.recompute_budget_move()
        self.assertEqual(
            bill1.budget_move_ids[0].date,
            bill1.invoice_line_ids[0].date_commit,
        )
