# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

from freezegun import freeze_time

from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests import Form, tagged

from .common import get_budget_common_class


@tagged("post_install", "-at_install")
class TestBudgetControl(get_budget_common_class()):
    @classmethod
    @freeze_time("2001-02-01")
    def setUpClass(cls):
        super().setUpClass()

        # Create budget plan with 2 analytic
        lines = [
            Command.create(
                {"analytic_account_id": cls.costcenter1.id, "amount": 2400.0}
            ),
            Command.create(
                {"analytic_account_id": cls.costcenterX.id, "amount": 2400.0}
            ),
        ]
        cls.budget_plan = cls.create_budget_plan(
            cls,
            name="Test - Plan {cls.budget_period.name}",
            budget_period=cls.budget_period,
            lines=lines,
        )
        cls.budget_plan.action_confirm()
        cls.budget_plan.action_create_update_budget_control()
        cls.budget_plan.action_done()

        # Refresh data
        cls.budget_plan.invalidate_recordset()

        # Budget Control 1
        cls.budget_control = cls.budget_plan.budget_control_ids[0]
        cls.budget_control.template_line_ids = [
            cls.template_line1.id,
            cls.template_line2.id,
            cls.template_line3.id,
        ]

        # Test item created for 3 kpi x 4 quarters = 12 budget items
        cls.budget_control.prepare_budget_control_matrix()
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

        # Budget Control 2
        cls.budget_control2 = cls.budget_plan.budget_control_ids[1]
        cls.budget_control2.template_line_ids = [
            cls.template_line1.id,
            cls.template_line2.id,
            cls.template_line3.id,
        ]

        # Test item created for 3 kpi x 4 quarters = 12 budget items
        cls.budget_control2.prepare_budget_control_matrix()
        assert len(cls.budget_control2.line_ids) == 12
        # Assign budget.control amount: KPI1 = 100x4=400, KPI2=800, KPI3=1,200
        cls.budget_control2.line_ids.filtered(lambda x: x.kpi_id == cls.kpi1).write(
            {"amount": 100}
        )
        cls.budget_control2.line_ids.filtered(lambda x: x.kpi_id == cls.kpi2).write(
            {"amount": 200}
        )
        cls.budget_control2.line_ids.filtered(lambda x: x.kpi_id == cls.kpi3).write(
            {"amount": 300}
        )

        # Multi-Currency
        cls.other_currency = cls.env.ref("base.EUR")
        cls.other_currency.active = True
        cls.company_c = cls.env["res.company"].create(
            {"name": "Test Company C", "currency_id": cls.other_currency.id}
        )

    def _create_invoice(
        self, inv_type, vendor, invoice_date, analytic_distribution, invoice_lines
    ):
        invoice = self.Move.create(
            {
                "move_type": inv_type,
                "partner_id": vendor.id,
                "invoice_date": invoice_date,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "quantity": 1,
                            "account_id": il.get("account"),
                            "price_unit": il.get("price_unit"),
                            "analytic_distribution": analytic_distribution,
                        },
                    )
                    for il in invoice_lines
                ],
            }
        )
        return invoice

    @freeze_time("2001-02-01")
    def test_01_budget_plan_create_line_from_wizard(self):
        self.assertEqual(len(self.budget_plan.line_ids), 2)
        self.assertAlmostEqual(self.budget_plan.total_amount, 4800)  # 2 budget 2400*2
        self.assertEqual(self.budget_plan.state, "done")

        # Reset plan to draft for add new analytic
        self.budget_plan.action_cancel()
        self.assertEqual(self.budget_plan.state, "cancel")

        self.budget_plan.action_draft()
        self.assertEqual(self.budget_plan.state, "draft")

        action = self.budget_plan.action_get_all_analytic_accounts()
        self.assertEqual(action["res_model"], "budget.plan.analytic.select")

        # Create with no active_id, it should nothing to do
        wizard = self.PlanAnalyticSelect.create({"analytic_account_ids": []})
        action = wizard.action_add()
        self.assertEqual(len(self.budget_plan.line_ids), 2)

        # Create with empty analytic, it should remove all plan lines
        wizard = self.PlanAnalyticSelect.with_context(
            active_id=self.budget_plan.id
        ).create({"analytic_account_ids": []})
        wizard.action_add()
        self.assertEqual(len(self.budget_plan.line_ids), 0)

        # Create with multi analytic
        wizard = self.PlanAnalyticSelect.with_context(
            active_id=self.budget_plan.id
        ).create({"analytic_account_ids": [self.costcenter1.id, self.costcenterX.id]})
        wizard.action_add()
        self.assertEqual(len(self.budget_plan.line_ids), 2)

    @freeze_time("2001-02-01")
    def test_02_budget_plan_check_duplicate_aa(self):
        with self.assertRaisesRegex(UserError, "Duplicate analytic account found:"):
            self.budget_plan.line_ids.create(
                {
                    "analytic_account_id": self.costcenter1.id,
                    "plan_id": self.budget_plan.id,
                }
            )

    @freeze_time("2001-02-01")
    def test_03_budget_plan_check_control(self):
        self.assertEqual(len(self.budget_plan.budget_control_ids), 2)
        action = self.budget_plan.button_open_budget_control()
        self.assertEqual(
            action["domain"][0][2], self.budget_plan.budget_control_ids.ids
        )

    @freeze_time("2001-02-01")
    def test_04_budget_control_check_control_analytic(self):
        """Check control analytic account in budget control"""
        analytic_distribution = {self.costcenter1.id: 100}
        bill1 = self._create_simple_bill(analytic_distribution, self.account_kpiX, 100)

        # Step1: Use account with not in templatee, it should error
        with self.assertRaisesRegex(UserError, "is not valid in template"):
            bill1.action_post()
        # Add account code in template
        self.template_line1.account_ids = [(4, self.account_kpiX.id)]
        # Post again, it should not error
        bill1.button_draft()
        bill1.action_post()

        # Step2: Control budget in period, but budget control is not control
        self.budget_period.control_budget = True
        self.assertEqual(self.budget_period.control_level, "analytic_kpi")
        self.assertTrue(self.budget_period.control_all_analytic_accounts)
        bill1.button_draft()
        # Now, budget_control is not yet set to Done, raise error when post invoice
        self.assertEqual(self.budget_control.state, "draft")
        message_error = (
            "Budget control sheets for the following analytics are not in control:"
        )
        with self.assertRaisesRegex(UserError, message_error):
            bill1.action_post()
        bill1.button_draft()

        # Step3: Delete template line1 for test KPI not in control
        self.budget_control.template_line_ids = [
            self.template_line2.id,
            self.template_line3.id,
        ]
        self.budget_control.prepare_budget_control_matrix()
        self.budget_control.line_ids[0].write({"amount": 2400})
        self.budget_control.action_submit()
        self.budget_control.action_done()

        # View monitoring from budget control
        action = self.budget_control.action_view_monitoring()
        self.assertEqual(action["res_model"], "budget.monitor.report")
        self.assertEqual(
            action["domain"][0][2], self.budget_control.analytic_account_id.id
        )

        # KPI not in control -> lock
        with self.assertRaisesRegex(UserError, "not valid for budgeting"):
            bill1.action_post()

    @freeze_time("2001-02-01")
    def test_05_budget_control_check_control_some_aa(self):
        analytic_distribution = {self.costcenter1.id: 100}
        self.assertTrue(self.budget_period.control_all_analytic_accounts)
        self.budget_period.write(
            {
                "control_budget": True,
                "control_all_analytic_accounts": False,
            }
        )

        # No control analytic -> No Lock
        self.assertFalse(self.budget_period.control_analytic_account_ids)
        bill1 = self._create_simple_bill(
            analytic_distribution, self.account_kpi1, 100000
        )
        bill1.action_post()
        self.assertTrue(bill1.budget_move_ids)
        # Return budget
        bill1.button_draft()
        self.assertFalse(bill1.budget_move_ids)

        # Valid KPI + analytic in control_analytic_account_ids
        self.budget_control.action_submit()
        self.budget_control.action_done()

        self.budget_period.control_analytic_account_ids = self.costcenter1
        bill2 = self._create_simple_bill(
            analytic_distribution, self.account_kpi1, 100000
        )
        # Check budget
        with self.assertRaisesRegex(UserError, "Budget not sufficient,"):
            bill2.action_post()

    @freeze_time("2001-02-01")
    def test_06_budget_control_check_soft_hard_reset(self):
        self.assertAlmostEqual(self.budget_control.amount_balance, 2400.0)
        # Test Soft Reset, Amount should be 2400 (no change)
        self.budget_control.with_context(
            keep_item_amount=1
        ).prepare_budget_control_matrix()
        self.assertAlmostEqual(self.budget_control.amount_balance, 2400.0)
        # Test Hard Reset, Amount should be 0
        self.budget_control.prepare_budget_control_matrix()
        self.assertAlmostEqual(self.budget_control.amount_balance, 0.0)

    @freeze_time("2001-02-01")
    def test_07_control_level_analytic_kpi(self):
        """
        Budget Period set control_level to "analytic_kpi", check at KPI level
        If amount exceed 400, lock budget
        """
        self.budget_period.control_budget = True
        self.budget_period.control_level = "analytic_kpi"
        analytic_distribution = {self.costcenter1.id: 100}
        # Budget Controlled
        self.budget_control.action_submit()
        self.budget_control.action_done()
        # Test with amount = 401
        bill1 = self._create_simple_bill(analytic_distribution, self.account_kpi1, 401)
        with self.assertRaises(UserError):
            bill1.action_post()

    @freeze_time("2001-02-01")
    def test_08_control_level_analytic(self):
        """
        Budget Period set control_level to "analytic", check at Analytic level
        If amount exceed 400, not lock budget and still has balance after that
        """
        self.budget_period.control_budget = True
        self.budget_period.control_level = "analytic"
        analytic_distribution = {self.costcenter1.id: 100}
        # Budget Controlled
        self.budget_control.action_submit()
        self.budget_control.action_done()
        # Test with amount = 500
        bill1 = self._create_simple_bill(analytic_distribution, self.account_kpi1, 500)
        bill1.action_post()
        self.assertEqual(bill1.state, "posted")
        self.assertTrue(self.budget_control.amount_balance)

    @freeze_time("2001-02-01")
    def test_09_no_account_budget_check(self):
        """If budget.period is not set to check budget, no budget check in all cases"""
        # No budget check
        self.budget_period.control_budget = False
        analytic_distribution = {self.costcenter1.id: 100}
        # Budget Controlled
        self.budget_control.action_submit()
        self.budget_control.action_done()
        # Create big amount invoice transaction > 2400
        bill1 = self._create_simple_bill(
            analytic_distribution, self.account_kpi1, 100000
        )
        bill1.action_post()
        self.assertTrue(bill1.budget_move_ids)

    @freeze_time("2001-02-01")
    def test_10_refund_no_budget_check(self):
        """For refund, always not checking"""
        # First, make budget actual to exceed budget first
        self.budget_period.control_budget = False  # No budget check first
        analytic_distribution = {self.costcenter1.id: 100}
        # Budget Controlled
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.assertEqual(self.budget_control.amount_balance, 2400)
        bill1 = self._create_simple_bill(
            analytic_distribution, self.account_kpi1, 100000
        )
        bill1.action_post()
        # Update budget info
        self.budget_control.invalidate_recordset()
        self.assertEqual(self.budget_control.amount_balance, -97600)

        # Check budget, for in_refund, force no budget check
        self.budget_period.control_budget = True
        self.budget_control.action_draft()
        invoice = self._create_invoice(
            "in_refund",
            self.vendor,
            datetime.today(),
            analytic_distribution,
            [{"account": self.account_kpi1.id, "price_unit": 100}],
        )
        invoice.action_post()
        # Update budget info
        self.budget_control.invalidate_recordset()
        self.assertEqual(self.budget_control.amount_balance, -97500)

    @freeze_time("2001-02-01")
    def test_11_auto_date_commit(self):
        """
        - Budget move's date_commit should follow that in _budget_date_commit_fields
        - If date_commit is not inline with analytic date range, adjust it automatically
        - Use the auto date_commit to create budget move
        - On cancel of document (unlink budget moves), date_commit is set to False
        """
        self.budget_period.control_budget = False
        # First setup self.costcenterX valid date range and auto adjust
        self.costcenterX.bm_date_from = "2001-01-01"
        self.costcenterX.bm_date_to = "2001-12-31"
        analytic_distribution = {self.costcenterX.id: 100}
        self.costcenterX.auto_adjust_date_commit = True
        # date_commit should follow that in _budget_date_commit_fields
        self.assertIn(
            "move_id.date",
            self.env["account.move.line"]._budget_date_commit_fields,
        )
        bill1 = self._create_simple_bill(analytic_distribution, self.account_kpi1, 10)
        bill1.invoice_date = "2001-05-05"
        bill1.date = "2001-05-05"
        bill1.action_post()
        self.assertEqual(bill1.invoice_date, bill1.budget_move_ids.mapped("date")[0])

        # If date is out of range, adjust automatically, to analytic date range
        self.assertIn(
            "move_id.date",
            self.env["account.move.line"]._budget_date_commit_fields,
        )
        bill2 = self._create_simple_bill(analytic_distribution, self.account_kpi1, 10)
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

    def test_12_manual_date_commit_check(self):
        """
        - If date_commit is not inline with analytic date range, show error
        """
        self.budget_period.control_budget = False
        analytic_distribution = {self.costcenterX.id: 100}
        # First setup self.costcenterX valid date range and auto adjust
        self.costcenterX.bm_date_from = "2001-01-01"
        self.costcenterX.bm_date_to = "2001-12-31"
        self.costcenterX.auto_adjust_date_commit = True
        # Manual Date Commit
        bill1 = self._create_simple_bill(analytic_distribution, self.account_kpiX, 10)
        bill1.invoice_date = "2001-05-05"
        bill1.date = "2001-05-05"
        # Use manual date_commit = "2002-10-10" which is not in range.
        bill1.invoice_line_ids[0].date_commit = "2002-10-10"
        with self.assertRaisesRegex(
            UserError, "Budget date commit is not within date range of"
        ):
            bill1.action_post()

    @freeze_time("2001-02-01")
    def test_13_force_no_budget_check(self):
        """
        By passing context["force_no_budget_check"] = True, no check in all case
        """
        self.budget_period.control_budget = True
        analytic_distribution = {self.costcenter1.id: 100}
        # Budget Controlled
        self.budget_control.allocated_amount = 2400
        self.budget_control.action_done()
        # Test with bit amount
        bill1 = self._create_simple_bill(
            analytic_distribution, self.account_kpi1, 100000
        )
        bill1.with_context(force_no_budget_check=True).action_post()
        self.assertTrue(bill1.budget_move_ids)

    def test_14_recompute_budget_move_date_commit(self):
        """
        - Date budget commit should be the same after recompute
        """
        self.budget_period.control_budget = False
        analytic_distribution = {self.costcenterX.id: 100}
        self.costcenterX.auto_adjust_date_commit = True

        bill1 = self._create_simple_bill(analytic_distribution, self.account_kpiX, 10)
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

    @freeze_time("2001-02-01")
    def test_15_budget_control_analytic_exceed_percent(self):
        """Check control analytic account exceed 100%"""
        analytic_distribution = {self.costcenter1.id: 130}
        bill1 = self._create_simple_bill(analytic_distribution, self.account_kpi1, 100)
        with self.assertRaisesRegex(
            UserError,
            "The total sum percent of Analytic Account must 100%. Please check again.",
        ):
            bill1.action_post()

    @freeze_time("2001-02-01")
    def test_16_budget_transfer(self):
        """Budget Transfer Process"""
        # Transfer from budget_control to budget_control2
        transfer = self._create_budget_transfer(
            budget_from=self.budget_control, budget_to=self.budget_control2, amount=0.0
        )
        self.assertEqual(len(transfer.transfer_item_ids), 1)
        self.assertAlmostEqual(self.budget_control.released_amount, 2400.0)
        self.assertAlmostEqual(self.budget_control2.released_amount, 2400.0)
        self.assertNotEqual(transfer.name, "/")
        # Amount transfer available is not 0.0
        self.assertNotEqual(transfer.transfer_item_ids.amount_from_available, 0.0)
        self.assertNotEqual(transfer.transfer_item_ids.amount_to_available, 0.0)

        # It should error
        with self.assertRaisesRegex(UserError, "Transfer amount must be positive!"):
            transfer.action_submit()

        # Transfer with 2500.0 (exceed budget)
        transfer.transfer_item_ids.write({"amount": 2500.0})
        with self.assertRaisesRegex(UserError, "Transfer amount can not be exceeded"):
            transfer.action_submit()

        transfer.transfer_item_ids.write({"amount": 40.0})
        transfer.action_submit()
        self.assertEqual(transfer.state, "submit")

        transfer.action_transfer()
        self.assertEqual(transfer.state, "transfer")
        self.assertEqual(len(self.budget_control.transfer_item_ids), 1)
        self.assertAlmostEqual(self.budget_control.released_amount, 2360.0)
        self.assertAlmostEqual(self.budget_control.transferred_amount, -40.0)
        self.assertEqual(len(self.budget_control2.transfer_item_ids), 1)
        self.assertAlmostEqual(self.budget_control2.released_amount, 2440.0)
        self.assertAlmostEqual(self.budget_control2.transferred_amount, 40.0)

        # Plan-line Allocated remains the original funding while Released
        # follows the completed transfers.
        self.budget_plan.check_plan_consumed()
        plan_line_from = self.budget_plan.line_ids.filtered(
            lambda line: line.analytic_account_id == self.costcenter1
        )
        plan_line_to = self.budget_plan.line_ids.filtered(
            lambda line: line.analytic_account_id == self.costcenterX
        )
        self.assertAlmostEqual(plan_line_from.allocated_amount, 2400.0)
        self.assertAlmostEqual(plan_line_from.released_amount, 2360.0)
        self.assertAlmostEqual(plan_line_to.allocated_amount, 2400.0)
        self.assertAlmostEqual(plan_line_to.released_amount, 2440.0)

        # Check snart button budget_control to transfer_items
        action_transfer_from = self.budget_control.action_open_budget_transfer_item()
        self.assertEqual(action_transfer_from["res_model"], "budget.transfer.item")
        self.assertEqual(
            action_transfer_from["domain"][0][2],
            self.budget_control.transfer_item_ids.ids,
        )

        action_transfer_to = self.budget_control.action_open_budget_transfer_item()
        self.assertEqual(action_transfer_to["res_model"], "budget.transfer.item")
        self.assertEqual(
            action_transfer_to["domain"][0][2],
            self.budget_control2.transfer_item_ids.ids,
        )

        # Don't allow delete transfer document if not draft state
        with self.assertRaisesRegex(
            UserError, "You are trying to delete a record that is still referenced!"
        ):
            transfer.unlink()

        transfer.action_reverse()
        self.budget_control._compute_transferred_amount()
        self.assertEqual(transfer.state, "reverse")
        self.assertEqual(len(self.budget_control.transfer_item_ids), 1)
        self.assertAlmostEqual(self.budget_control.released_amount, 2400.0)
        self.assertAlmostEqual(self.budget_control.transferred_amount, 0.0)
        self.budget_control2._compute_transferred_amount()
        self.assertEqual(len(self.budget_control2.transfer_item_ids), 1)
        self.assertAlmostEqual(self.budget_control2.released_amount, 2400.0)
        self.assertAlmostEqual(self.budget_control2.transferred_amount, 0.0)
        self.budget_plan.check_plan_consumed()
        self.assertAlmostEqual(plan_line_from.released_amount, 2400.0)
        self.assertAlmostEqual(plan_line_to.released_amount, 2400.0)

    @freeze_time("2001-02-01")
    def test_17_budget_adjustment(self):
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
        # balance in budget control must be 'Decrease'
        budget_adjust.action_adjust()
        self.assertEqual(self.budget_control.amount_balance, 2300.0)

    def test_18_budget_carry_forward(self):
        """NOTE: This test is not yet implemented for budget_control"""
        budget_commit_forward = self.CommitForward.create(
            {
                "name": "Test: Budget Carry Forward",
                "to_budget_period_id": self.budget_period.id,
            }
        )
        # Nothing to do, as no budget_commit
        budget_commit_forward.action_review_budget_commit()
        self.assertEqual(budget_commit_forward.state, "review")

        budget_commit_forward._compute_missing_analytic()

        res = budget_commit_forward.preview_budget_commit_forward_info()
        self.assertEqual(res["context"]["default_forward_id"], budget_commit_forward.id)

        budget_commit_forward.action_cancel()
        self.assertEqual(budget_commit_forward.state, "cancel")

        budget_commit_forward.action_draft()
        self.assertEqual(budget_commit_forward.state, "draft")

    def test_18a_budget_balance_forward_monitoring(self):
        """A completed balance forward must reduce the source availability."""
        BudgetPeriod = self.env["budget.period"]
        BalanceForward = self.env["budget.balance.forward"]
        BalanceForwardLine = self.env["budget.balance.forward.line"]
        MonitorReport = self.env["budget.monitor.report"]

        next_period = BudgetPeriod.create(
            {
                "name": f"Budget for FY{self.year + 1}",
                "template_id": self.template.id,
                "bm_date_from": f"{self.year + 1}-01-01",
                "bm_date_to": f"{self.year + 1}-12-31",
                "plan_date_range_type_id": self.date_range_type.id,
                "control_level": "analytic_kpi",
            }
        )
        forward = BalanceForward.create(
            {
                "name": "Test: Budget Balance Forward",
                "from_budget_period_id": self.budget_period.id,
                "to_budget_period_id": next_period.id,
            }
        )
        forward_line = BalanceForwardLine.create(
            {
                "forward_id": forward.id,
                "analytic_account_id": self.costcenter1.id,
                "amount_balance": 30.0,
                "amount_balance_forward": 20.0,
                "accumulate_analytic_account_id": self.costcenter1.id,
            }
        )
        next_plan_vals = {
            "name": "Budget Plan FY Next",
            "budget_period_id": next_period.id,
            "line_ids": [
                Command.create(
                    {
                        "analytic_account_id": self.costcenter1.id,
                        "amount": 20.0,
                    }
                )
            ],
        }
        # budget_plan_detail overrides total_amount to use detail lines until
        # the plan is confirmed.  This core test intentionally exercises the
        # plan-line flow, so make that mode explicit when the optional module
        # is installed (as it is in the full CI test suite).
        if "is_confirm_plan" in self.BudgetPlan._fields:
            next_plan_vals["is_confirm_plan"] = True
        next_plan = self.BudgetPlan.create(next_plan_vals)
        self.assertEqual(self.budget_control.amount_balance, 2400.0)
        self.assertEqual(next_plan.line_ids.amount_forward_in, 0.0)
        self.assertEqual(next_plan.line_ids.allocated_amount, 20.0)

        forward.action_budget_balance_forward()
        self.assertEqual(self.budget_control.amount_balance, 2370.0)
        self.assertEqual(next_plan.line_ids.amount_forward_in, 30.0)
        self.assertEqual(next_plan.line_ids.allocated_amount, 50.0)

        # A line change must invalidate cached Plan and Control totals.
        forward_line.amount_balance = 40.0
        self.assertEqual(next_plan.line_ids.amount_forward_in, 40.0)
        self.assertEqual(next_plan.line_ids.allocated_amount, 60.0)
        forward_line.amount_balance = 30.0
        self.assertEqual(next_plan.line_ids.amount_forward_in, 30.0)
        self.assertEqual(next_plan.line_ids.allocated_amount, 50.0)

        next_plan.check_plan_consumed()
        next_plan.action_create_update_budget_control()
        target_control = self.BudgetControl.search(
            [
                ("budget_period_id", "=", next_period.id),
                ("analytic_account_id", "=", self.costcenter1.id),
            ]
        )
        self.assertEqual(len(target_control), 1)
        self.assertNotEqual(target_control, self.budget_control)
        self.assertEqual(target_control.allocated_amount, 50.0)
        target_line = self.env["budget.control.line"].create(
            {
                "budget_control_id": target_control.id,
                "analytic_account_id": self.costcenter1.id,
                "date_from": next_period.bm_date_from,
                "date_to": next_period.bm_date_to,
                "amount": 50.0,
            }
        )
        target_control.allocated_amount = target_line.amount

        self.assertEqual(self.budget_control.amount_forward_out, 30.0)
        self.assertEqual(self.budget_control.amount_balance, 2370.0)
        self.assertEqual(target_control.amount_forward_in, 30.0)
        self.assertEqual(target_control.amount_new_budget, 20.0)
        self.assertEqual(target_control.amount_budget, 50.0)
        self.assertEqual(target_control.amount_balance, 50.0)
        self.assertEqual(next_plan.line_ids.amount_forward_in, 30.0)
        self.assertEqual(next_plan.line_ids.allocated_amount, 50.0)
        self.assertEqual(next_plan.line_ids.released_amount, 50.0)
        self.assertEqual(next_plan.total_amount, 50.0)
        target_control.action_submit()
        self.assertEqual(target_control.state, "submit")

        carry_only_plan = self.BudgetPlan.create(
            {
                "name": "Carry Only Budget Plan FY Next",
                "budget_period_id": next_period.id,
                "line_ids": [
                    Command.create(
                        {
                            "analytic_account_id": self.costcenter1.id,
                            "amount": 0.0,
                        }
                    )
                ],
            }
        )
        carry_only_plan.check_plan_consumed()
        self.assertEqual(carry_only_plan.line_ids.allocated_amount, 30.0)
        target_monitoring = target_control.action_view_monitoring()
        self.assertIn(
            ("budget_period_id", "=", next_period.id),
            target_monitoring["domain"],
        )

        fields = ["budget_period_id", "amount_type", "amount"]
        groupby = ["budget_period_id", "amount_type"]
        source_data = MonitorReport.read_group(
            [
                ("analytic_account_id", "=", self.costcenter1.id),
                ("budget_period_id", "=", self.budget_period.id),
            ],
            fields,
            groupby,
            lazy=False,
        )
        target_data = MonitorReport.read_group(
            [
                ("analytic_account_id", "=", self.costcenter1.id),
                ("budget_period_id", "=", next_period.id),
            ],
            fields,
            groupby,
            lazy=False,
        )
        source_amounts = {row["amount_type"]: row["amount"] for row in source_data}
        target_amounts = {row["amount_type"]: row["amount"] for row in target_data}
        self.assertEqual(source_amounts["12_forward_out"], -30.0)
        self.assertNotIn("11_forward_in", target_amounts)
        self.assertEqual(target_amounts["10_budget"], 50.0)
        self.assertEqual(sum(target_amounts.values()), 50.0)

        with self.assertRaisesRegex(UserError, "Reverse Forward"):
            forward.action_cancel()
        self.assertEqual(forward.state, "done")
        self.assertEqual(self.budget_control.amount_balance, 2370.0)
        self.assertEqual(next_plan.line_ids.allocated_amount, 50.0)

        # Cancellation is safe before a target Plan or Control enters workflow.
        cancellable_forward = BalanceForward.create(
            {
                "name": "Test: Cancellable Budget Balance Forward",
                "from_budget_period_id": self.budget_period.id,
                "to_budget_period_id": next_period.id,
            }
        )
        BalanceForwardLine.create(
            {
                "forward_id": cancellable_forward.id,
                "analytic_account_id": self.costcenterX.id,
                "amount_balance": 10.0,
                "amount_balance_forward": 10.0,
            }
        )
        self.assertEqual(self.budget_control2.amount_balance, 2400.0)
        cancellable_forward.action_budget_balance_forward()
        self.assertEqual(self.budget_control2.amount_balance, 2390.0)
        cancellable_forward.action_cancel()
        self.assertEqual(self.budget_control2.amount_balance, 2400.0)

        with self.assertRaisesRegex(ValidationError, "cannot be negative"):
            self.BudgetPlan.create(
                {
                    "name": "Invalid Negative Budget",
                    "budget_period_id": next_period.id,
                    "line_ids": [
                        Command.create(
                            {
                                "analytic_account_id": self.costcenterX.id,
                                "amount": -1.0,
                            }
                        )
                    ],
                }
            )

    @freeze_time("2001-02-01")
    def test_18b_balance_forward_same_analytic(self):
        """Forward balance on the same analytic reduces source and cancels safely."""
        BalanceForwardLine = self.env["budget.balance.forward.line"]

        next_period = self.env["budget.period"].create(
            {
                "name": f"Budget for FY{self.year + 1}",
                "template_id": self.template.id,
                "bm_date_from": f"{self.year + 1}-01-01",
                "bm_date_to": f"{self.year + 1}-12-31",
                "plan_date_range_type_id": self.date_range_type.id,
                "control_level": "analytic_kpi",
            }
        )
        forward = self.env["budget.balance.forward"].create(
            {
                "name": "Test: Same Analytic Forward",
                "from_budget_period_id": self.budget_period.id,
                "to_budget_period_id": next_period.id,
            }
        )
        BalanceForwardLine.create(
            {
                "forward_id": forward.id,
                "analytic_account_id": self.costcenter1.id,
                "amount_balance": 500.0,
                "amount_balance_forward": 500.0,
            }
        )
        # No bm_date_to -> the same analytic is reused as destination.
        self.assertEqual(
            forward.forward_line_ids.to_analytic_account_id, self.costcenter1
        )

        next_plan_vals = {
            "name": "Same Analytic Plan FY Next",
            "budget_period_id": next_period.id,
            "line_ids": [
                Command.create(
                    {"analytic_account_id": self.costcenter1.id, "amount": 100.0}
                )
            ],
        }
        # Keep this core scenario on plan lines when budget_plan_detail is
        # installed in the full CI suite. Its test helper otherwise creates
        # default detail lines and replaces the explicit 100.0 with 2400.0.
        if "is_confirm_plan" in self.BudgetPlan._fields:
            next_plan_vals["is_confirm_plan"] = True
        next_plan = self.BudgetPlan.create(next_plan_vals)
        # Draft forward is not counted yet.
        self.assertEqual(next_plan.line_ids.amount_forward_in, 0.0)

        forward.action_budget_balance_forward()
        self.budget_control.invalidate_recordset()
        next_plan.invalidate_recordset()
        # Source: 2400 - 500 forwarded out = 1900.
        self.assertEqual(self.budget_control.amount_forward_out, 500.0)
        self.assertEqual(self.budget_control.amount_balance, 1900.0)
        self.costcenter1.invalidate_recordset()
        self.assertEqual(self.costcenter1.amount_forward_out, 500.0)
        # Target: 500 forwarded in + 100 new = 600 available.
        self.assertEqual(next_plan.line_ids.amount_forward_in, 500.0)
        self.assertEqual(next_plan.line_ids.allocated_amount, 600.0)

        # --- Cancel a forward whose target is not yet in any workflow ---
        cancellable = self.env["budget.balance.forward"].create(
            {
                "name": "Test: Cancellable Same Analytic Forward",
                "from_budget_period_id": self.budget_period.id,
                "to_budget_period_id": next_period.id,
            }
        )
        BalanceForwardLine.create(
            {
                "forward_id": cancellable.id,
                "analytic_account_id": self.costcenterX.id,
                "amount_balance": 100.0,
                "amount_balance_forward": 100.0,
            }
        )
        self.budget_control2.invalidate_recordset()
        cancellable.action_budget_balance_forward()
        self.budget_control2.invalidate_recordset()
        self.assertEqual(self.budget_control2.amount_balance, 2300.0)
        cancellable.action_cancel()
        self.budget_control2.invalidate_recordset()
        # Cancel restores the source balance.
        self.assertEqual(self.budget_control2.amount_balance, 2400.0)

    @freeze_time("2001-02-01")
    def test_18c_balance_forward_different_analytic(self):
        """Forward balance to a different analytic (method_type 'new')
        tracks correctly."""
        BalanceForwardLine = self.env["budget.balance.forward.line"]
        MonitorReport = self.env["budget.monitor.report"]

        # Source analytic ends before the next period -> method_type 'new'.
        self.costcenter1.bm_date_to = f"{self.year}-12-31"
        next_period = self.env["budget.period"].create(
            {
                "name": f"Budget for FY{self.year + 1}",
                "template_id": self.template.id,
                "bm_date_from": f"{self.year + 1}-01-01",
                "bm_date_to": f"{self.year + 1}-12-31",
                "plan_date_range_type_id": self.date_range_type.id,
                "control_level": "analytic_kpi",
            }
        )
        # The destination analytic is resolved via next_year_analytic().
        next_analytic = self.costcenter1.next_year_analytic(auto_create=True)
        self.assertNotEqual(next_analytic, self.costcenter1)
        forward = self.env["budget.balance.forward"].create(
            {
                "name": "Test: Different Analytic Forward",
                "from_budget_period_id": self.budget_period.id,
                "to_budget_period_id": next_period.id,
            }
        )
        BalanceForwardLine.create(
            {
                "forward_id": forward.id,
                "analytic_account_id": self.costcenter1.id,
                "amount_balance": 300.0,
                "amount_balance_forward": 300.0,
                "method_type": "new",
            }
        )
        self.assertEqual(forward.forward_line_ids.to_analytic_account_id, next_analytic)

        next_plan = self.create_budget_plan(
            name="Different Analytic Plan FY Next",
            budget_period=next_period,
            lines=[
                Command.create(
                    {"analytic_account_id": next_analytic.id, "amount": 200.0}
                )
            ],
        )
        forward.action_budget_balance_forward()
        self.budget_control.invalidate_recordset()
        next_plan.invalidate_recordset()
        # Source: 2400 - 300 forwarded out = 2100.
        self.assertEqual(self.budget_control.amount_forward_out, 300.0)
        self.assertEqual(self.budget_control.amount_balance, 2100.0)
        # Target: 300 forwarded in + 200 new = 500 available.
        self.assertEqual(next_plan.line_ids.amount_forward_in, 300.0)
        self.assertEqual(next_plan.line_ids.allocated_amount, 500.0)

        # Build the target budget control and verify its breakdown.
        next_plan.action_create_update_budget_control()
        target_control = self.BudgetControl.search(
            [
                ("budget_period_id", "=", next_period.id),
                ("analytic_account_id", "=", next_analytic.id),
            ]
        )
        self.env["budget.control.line"].create(
            {
                "budget_control_id": target_control.id,
                "analytic_account_id": next_analytic.id,
                "date_from": next_period.bm_date_from,
                "date_to": next_period.bm_date_to,
                "amount": 500.0,
            }
        )
        target_control.allocated_amount = 500.0
        target_control.invalidate_recordset()
        self.assertEqual(target_control.amount_forward_in, 300.0)
        self.assertEqual(target_control.amount_new_budget, 200.0)
        self.assertEqual(target_control.amount_budget, 500.0)

        # Monitoring keeps the signed negative ledger amount; the target analytic
        # only exposes its budget line (forward_in stays out to avoid duplicates).
        report_fields = ["amount_type", "amount"]
        groupby = ["amount_type"]
        source_data = MonitorReport.read_group(
            [
                ("analytic_account_id", "=", self.costcenter1.id),
                ("budget_period_id", "=", self.budget_period.id),
            ],
            report_fields,
            groupby,
            lazy=False,
        )
        source_amounts = {row["amount_type"]: row["amount"] for row in source_data}
        self.assertEqual(source_amounts["12_forward_out"], -300.0)
        target_data = MonitorReport.read_group(
            [
                ("analytic_account_id", "=", next_analytic.id),
                ("budget_period_id", "=", next_period.id),
            ],
            report_fields,
            groupby,
            lazy=False,
        )
        target_amounts = {row["amount_type"]: row["amount"] for row in target_data}
        self.assertNotIn("11_forward_in", target_amounts)
        self.assertEqual(target_amounts["10_budget"], 500.0)

    @freeze_time("2001-02-01")
    def test_19_unmatched_account_bypass_and_policy(self):
        """
        account_kpiX is not in template. Test two bypass mechanisms:
        1. budget_bypass flag on account.account > always skip check
        2. unmatched_account_policy = 'skip' on budget.period > pass through
        Default policy 'error' still blocks.
        """
        self.budget_period.control_budget = True
        self.budget_period.control_level = "analytic_kpi"
        self.budget_control.action_submit()
        self.budget_control.action_done()

        analytic_distribution = {self.costcenter1.id: 100}

        # Baseline: default policy 'error' + no bypass > must raise
        self.assertEqual(self.budget_period.unmatched_account_policy, "error")
        bill = self._create_simple_bill(analytic_distribution, self.account_kpiX, 100)
        with self.assertRaisesRegex(UserError, "is not valid in template"):
            bill.action_post()

        # account.budget_bypass = True > skip regardless of policy
        self.account_kpiX.budget_bypass = True
        bill_bypass = self._create_simple_bill(
            analytic_distribution, self.account_kpiX, 100
        )
        bill_bypass.action_post()
        self.assertEqual(bill_bypass.state, "posted")
        self.assertTrue(bill_bypass.budget_move_ids)
        self.assertFalse(bill_bypass.budget_move_ids.mapped("template_line_id"))

        # Reset bypass, switch period policy to 'skip' > also passes through
        self.account_kpiX.budget_bypass = False
        self.budget_period.unmatched_account_policy = "skip"
        bill_skip = self._create_simple_bill(
            analytic_distribution, self.account_kpiX, 100
        )
        bill_skip.action_post()
        self.assertEqual(bill_skip.state, "posted")
        self.assertTrue(bill_skip.budget_move_ids)

    @freeze_time("2001-02-01")
    def test_20_multicompany_shared_budget_period(self):
        """
        1 shared BC (2400) via shared analytic (no company) used by 2 companies.
        - Company A posts 2000 -> ok, remaining 400
        - Company A posts 500 -> error (shared budget exhausted)
        - Company B posts 500 -> error (same shared pool, only 400 left)
        - Company B posts 300 -> ok, remaining 100 (2400 - 2000 A - 300 B)
        """
        company_b = self.company_b

        # Shared analytic (no company_id) ->
        # budget_company_ids stays empty -> all companies
        shared_aa = self.Analytic.create(
            {"name": "CC_Shared_test20", "plan_id": self.aa_plan1.id}
        )

        # Reuse existing budget_period;
        # company_ids empty = visible to all companies
        # Enable control_budget so check_budget() runs on post
        self.budget_period.write({"control_budget": True})

        # Standard BC creation flow via budget.plan
        budget_plan = self.create_budget_plan(
            name="Plan Shared 2001 (test_20)",
            budget_period=self.budget_period,
            lines=[
                Command.create({"analytic_account_id": shared_aa.id, "amount": 2400.0})
            ],
        )
        budget_plan.action_confirm()
        budget_plan.action_create_update_budget_control()
        budget_plan.invalidate_recordset()
        bc_shared = budget_plan.budget_control_ids
        self.assertEqual(len(bc_shared), 1)
        bc_shared.template_line_ids = [self.template_line1.id]
        bc_shared.prepare_budget_control_matrix()
        # 4 quarters x 1 KPI = 4 lines; set 600 each -> total 2400
        bc_shared.line_ids.write({"amount": 600})
        bc_shared.action_submit()
        bc_shared.action_done()

        # Expense account for company_b (each company needs its own code in Odoo 18)
        account_kpi1_b = self.Account.create(
            {
                "name": "KPI1 Company B (test_20)",
                "code": "KPI1.B20",
                "account_type": "expense",
                "company_ids": [Command.set([company_b.id])],
            }
        )
        self.template_line1.account_ids = [Command.link(account_kpi1_b.id)]
        # company_b payable + journal reuse from common.py setup
        journal_b = self.journal_purchase_b

        analytic_dist = {str(shared_aa.id): 100}

        # Step 1: Company A posts 2000 -> ok, remaining = 400
        bill_a1 = self.Move.create(
            {
                "move_type": "in_invoice",
                "partner_id": self.vendor.id,
                "invoice_date": "2001-02-01",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "quantity": 1,
                            "account_id": self.account_kpi1.id,
                            "price_unit": 2000,
                            "analytic_distribution": analytic_dist,
                        }
                    )
                ],
            }
        )
        bill_a1.action_post()
        self.assertEqual(bill_a1.state, "posted")
        bc_shared.invalidate_recordset()
        self.assertAlmostEqual(bc_shared.amount_balance, 400.0)

        # Step 2: Company A posts 500 -> error (only 400 left in shared pool)
        bill_a2 = self.Move.create(
            {
                "move_type": "in_invoice",
                "partner_id": self.vendor.id,
                "invoice_date": "2001-02-01",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "quantity": 1,
                            "account_id": self.account_kpi1.id,
                            "price_unit": 500,
                            "analytic_distribution": analytic_dist,
                        }
                    )
                ],
            }
        )
        with self.assertRaisesRegex(UserError, "Budget not sufficient"):
            bill_a2.action_post()
        bill_a2.button_draft()  # clean up budget moves from failed post

        # Step 3: Company B posts 500 -> error (same shared pool, 400 remaining)
        bill_b1 = self.Move.with_company(company_b).create(
            {
                "move_type": "in_invoice",
                "journal_id": journal_b.id,
                "partner_id": self.vendor.id,
                "invoice_date": "2001-02-01",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "quantity": 1,
                            "account_id": account_kpi1_b.id,
                            "price_unit": 500,
                            "analytic_distribution": analytic_dist,
                        }
                    )
                ],
            }
        )
        with self.assertRaisesRegex(UserError, "Budget not sufficient"):
            bill_b1.action_post()
        bill_b1.button_draft()  # clean up budget moves from failed post

        # Step 4: Company B posts 300 -> ok (300 < 400 remaining), remaining = 100
        bill_b2 = self.Move.with_company(company_b).create(
            {
                "move_type": "in_invoice",
                "journal_id": journal_b.id,
                "partner_id": self.vendor.id,
                "invoice_date": "2001-02-01",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "quantity": 1,
                            "account_id": account_kpi1_b.id,
                            "price_unit": 300,
                            "analytic_distribution": analytic_dist,
                        }
                    )
                ],
            }
        )
        bill_b2.action_post()
        self.assertEqual(bill_b2.state, "posted")
        bc_shared.invalidate_recordset()
        # 2400 - 2000 (Company A) - 300 (Company B) = 100
        self.assertAlmostEqual(bc_shared.amount_balance, 100.0)

    @freeze_time("2001-02-01")
    def test_21_multicompany_separate_budget(self):
        """
        1 BC per company (analytic_a: 2400, analytic_b: 2400), separate periods.
        - Company A posts 2000 -> ok, A remaining = 400
        - Company A posts 500 -> error (A budget exhausted)
        - Company B posts 500 -> ok, B remaining = 1900 (separate independent budget)
        """
        BudgetPeriod = self.env["budget.period"]
        company_a = self.env.company
        company_b = self.company_b

        # Separate analytics per company
        analytic_a = self.Analytic.create(
            {
                "name": "CC_A_test21",
                "plan_id": self.aa_plan1.id,
                "company_id": company_a.id,
            }
        )
        analytic_b = self.Analytic.create(
            {
                "name": "CC_B_test21",
                "plan_id": self.aa_plan1.id,
                "company_id": company_b.id,
            }
        )

        # Restrict existing budget_period to company_a;
        # create separate period_b for company_b
        self.budget_period.write(
            {
                "control_budget": True,
                "company_ids": [Command.set([company_a.id])],
            }
        )
        period_a = self.budget_period
        period_b = BudgetPeriod.create(
            {
                "name": "FY 2001 Company B (test_21)",
                "template_id": self.template.id,
                "bm_date_from": "2001-01-01",
                "bm_date_to": "2001-12-31",
                "plan_date_range_type_id": self.date_range_type.id,
                "control_level": "analytic_kpi",
                "control_budget": True,
                "company_ids": [Command.set([company_b.id])],
            }
        )

        # BC for company_a: analytic_a, 2400
        bc_a = self.BudgetControl.with_company(company_a).create(
            {
                "name": "BC_A test21",
                "budget_period_id": period_a.id,
                "analytic_account_id": analytic_a.id,
                "plan_date_range_type_id": self.date_range_type.id,
                "currency_id": company_a.currency_id.id,
                "allocated_amount": 2400.0,
                "template_line_ids": [Command.set([self.template_line1.id])],
                "line_ids": [
                    Command.create(
                        {
                            "date_from": "2001-01-01",
                            "date_to": "2001-12-31",
                            "template_line_id": self.template_line1.id,
                            "analytic_account_id": analytic_a.id,
                            "amount": 2400,
                        }
                    )
                ],
            }
        )
        bc_a.action_submit()
        bc_a.action_done()

        # BC for company_b: analytic_b, 2400
        account_kpi1_b = self.Account.create(
            {
                "name": "KPI1 Company B (test_21)",
                "code": "KPI1.B21",
                "account_type": "expense",
                "company_ids": [Command.set([company_b.id])],
            }
        )
        self.template_line1.account_ids = [Command.link(account_kpi1_b.id)]
        bc_b = self.BudgetControl.with_company(company_b).create(
            {
                "name": "BC_B test21",
                "budget_period_id": period_b.id,
                "analytic_account_id": analytic_b.id,
                "plan_date_range_type_id": self.date_range_type.id,
                "currency_id": company_b.currency_id.id,
                "allocated_amount": 2400.0,
                "template_line_ids": [Command.set([self.template_line1.id])],
                "line_ids": [
                    Command.create(
                        {
                            "date_from": "2001-01-01",
                            "date_to": "2001-12-31",
                            "template_line_id": self.template_line1.id,
                            "analytic_account_id": analytic_b.id,
                            "amount": 2400,
                        }
                    )
                ],
            }
        )
        bc_b.action_submit()
        bc_b.action_done()

        # company_b payable + journal reuse from common.py setup
        journal_b = self.journal_purchase_b

        # Step 1: Company A posts 2000 to analytic_a -> ok, A remaining = 400
        bill_a1 = self.Move.create(
            {
                "move_type": "in_invoice",
                "partner_id": self.vendor.id,
                "invoice_date": "2001-02-01",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "quantity": 1,
                            "account_id": self.account_kpi1.id,
                            "price_unit": 2000,
                            "analytic_distribution": {str(analytic_a.id): 100},
                        }
                    )
                ],
            }
        )
        bill_a1.action_post()
        self.assertEqual(bill_a1.state, "posted")
        bc_a.invalidate_recordset()
        self.assertAlmostEqual(bc_a.amount_balance, 400.0)

        # Step 2: Company A posts 500 to analytic_a -> error (only 400 left)
        bill_a2 = self.Move.create(
            {
                "move_type": "in_invoice",
                "partner_id": self.vendor.id,
                "invoice_date": "2001-02-01",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "quantity": 1,
                            "account_id": self.account_kpi1.id,
                            "price_unit": 500,
                            "analytic_distribution": {str(analytic_a.id): 100},
                        }
                    )
                ],
            }
        )
        with self.assertRaisesRegex(UserError, "Budget not sufficient"):
            bill_a2.action_post()
        bill_a2.button_draft()  # clean up budget moves from failed post

        # Step 3: Company B posts 500 to analytic_b -> ok, B remaining = 1900
        bill_b = self.Move.with_company(company_b).create(
            {
                "move_type": "in_invoice",
                "journal_id": journal_b.id,
                "partner_id": self.vendor.id,
                "invoice_date": "2001-02-01",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "quantity": 1,
                            "account_id": account_kpi1_b.id,
                            "price_unit": 500,
                            "analytic_distribution": {str(analytic_b.id): 100},
                        }
                    )
                ],
            }
        )
        bill_b.action_post()
        self.assertEqual(bill_b.state, "posted")
        bc_b.invalidate_recordset()
        self.assertAlmostEqual(bc_b.amount_balance, 1900.0)

    @freeze_time("2001-02-01")
    def test_22_budget_control_over_consumed(self):
        """analytic_kpi: lowering a KPI budget below already-consumed is blocked.

        _check_budget_control_over_consumed raises when editing line_ids would
        push a KPI's amount_balance negative.
        """
        self.budget_period.control_budget = True
        self.budget_control.action_submit()
        self.budget_control.action_done()
        # Consume 300 on KPI1 (budgeted 400) -> balance 100
        analytic_distribution = {self.costcenter1.id: 100}
        bill = self._create_simple_bill(analytic_distribution, self.account_kpi1, 300)
        bill.action_post()
        self.assertEqual(bill.state, "posted")
        self.budget_control.invalidate_recordset()
        # Lower KPI1 (4 quarters) to 50 each = 200 total < 300 consumed -> error.
        # Write through the parent so @api.constrains("line_ids") re-fires.
        kpi1_lines = self.budget_control.line_ids.filtered(
            lambda x: x.kpi_id == self.kpi1
        )
        with self.assertRaisesRegex(UserError, "Total amount in KPI"):
            self.budget_control.write(
                {
                    "line_ids": [
                        Command.update(line.id, {"amount": 50}) for line in kpi1_lines
                    ]
                }
            )

    def test_23_check_budget_company_allowed(self):
        """Analytic's own company must stay in Allowed Budget Companies."""
        company_a = self.env.company
        company_b = self.company_b
        analytic = self.Analytic.create(
            {
                "name": "CC_test23",
                "plan_id": self.aa_plan1.id,
                "company_id": company_a.id,
            }
        )
        # Own company auto-included in the allowed list
        self.assertIn(company_a, analytic.budget_company_ids)
        # Dropping the analytic's own company from the allowed list -> error
        with self.assertRaisesRegex(UserError, "must be in Allowed Budget Companies"):
            analytic.write({"budget_company_ids": [Command.set([company_b.id])]})

        # Allowed companies with mismatched currencies -> error
        with self.assertRaisesRegex(UserError, "use different currencies"):
            analytic.write(
                {"budget_company_ids": [Command.set([company_a.id, self.company_c.id])]}
            )

        # Test use multi currency on budget.control -> error
        with self.assertRaisesRegex(
            UserError, "sharing a budget must use the same currency"
        ):
            self.budget_control.write(
                {"company_ids": [Command.set([company_a.id, self.company_c.id])]}
            )

    @freeze_time("2001-02-01")
    def test_24_commit_cross_currency_blocked(self):
        """Test blocks commit when doc company currency != budget currency."""
        self.budget_period.control_budget = True
        self.budget_control.action_submit()
        self.budget_control.action_done()

        # BC is in main company currency; other_currency (EUR) must differ from it.
        self.assertNotEqual(self.budget_control.currency_id, self.other_currency)

        account_payable_c = self.Account.create(
            {
                "name": "Accounts Payable C (test_24)",
                "code": "AP.C24",
                "account_type": "liability_payable",
                "reconcile": True,
                "company_ids": [Command.set([self.company_c.id])],
            }
        )
        self.vendor.with_company(self.company_c).write(
            {"property_account_payable_id": account_payable_c.id}
        )
        journal_c = self.env["account.journal"].create(
            {
                "name": "Vendor Bills C (test_24)",
                "type": "purchase",
                "code": "VBC24",
                "company_id": self.company_c.id,
            }
        )
        account_kpi1_c = self.Account.create(
            {
                "name": "KPI1 Company C (test_24)",
                "code": "KPI1.C24",
                "account_type": "expense",
                "company_ids": [Command.set([self.company_c.id])],
            }
        )
        self.template_line1.account_ids = [Command.link(account_kpi1_c.id)]

        bill_c = self.Move.with_company(self.company_c).create(
            {
                "move_type": "in_invoice",
                "journal_id": journal_c.id,
                "partner_id": self.vendor.id,
                "invoice_date": "2001-02-01",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "quantity": 1,
                            "account_id": account_kpi1_c.id,
                            "price_unit": 100,
                            "analytic_distribution": {str(self.costcenter1.id): 100},
                        }
                    )
                ],
            }
        )
        with self.assertRaisesRegex(
            UserError, "All companies sharing a budget must use the same currency."
        ):
            bill_c.action_post()

    @freeze_time("2001-02-01")
    def test_25_required_analytic_setting(self):
        """'Required Analytic Account' setting enforces analytic on doclines.

        * account.move.line: only product lines are enforced; section / note
          lines are skipped (they are not product lines).
        * a docline with NO display_type field (budget.move.adjustment.item,
          same shape as PR / EX / AV) must also be enforced.

        Regression guard: a previous ``hasattr(self, "display_type")`` check made
        the requirement silently skip every docline whose model lacks the field
        (PR, EX, AV), letting those documents commit without an analytic account.
        """
        # Enable the "Required Analytic Account" setting for the current user.
        required_group = self.env.ref("budget_control.group_required_analytic")
        self.env.user.groups_id = [Command.link(required_group.id)]
        self.assertTrue(
            self.env.user.has_group("budget_control.group_required_analytic")
        )
        analytic_distribution = {self.costcenter1.id: 100}

        # account.move.line product line, no analytic -> blocked (Required)
        bill_no_aa = self._create_simple_bill(False, self.account_kpi1, 100)
        with self.assertRaisesRegex(UserError, "Please fill analytic account."):
            bill_no_aa.action_post()

        # account.move.line product line, with analytic -> posts (Not Required)
        bill_aa = self._create_simple_bill(
            analytic_distribution, self.account_kpi1, 100
        )
        bill_aa.action_post()
        self.assertEqual(bill_aa.state, "posted")

        # account.move.line: only product lines are enforced; everything else
        # on the move is skipped (Not Required).
        AML = self.env["account.move.line"]
        # section / note lines are not product lines
        self.assertFalse(
            AML.new({"display_type": "line_section"})._check_required_analytic()
        )
        self.assertFalse(
            AML.new({"display_type": "line_note"})._check_required_analytic()
        )
        # line on a "Not Affect Budget" move
        naf_move = self.env["account.move"].new({"not_affect_budget": True})
        self.assertFalse(
            AML.new(
                {"display_type": "product", "move_id": naf_move.id}
            )._check_required_analytic()
        )
        # tax line
        tax = self.env["account.tax"].new({})
        self.assertFalse(
            AML.new(
                {"display_type": "product", "tax_line_id": tax.id}
            )._check_required_analytic()
        )
        # payment entry (auto-generated from account.payment)
        payment_move = self.env["account.move"].new(
            {"move_type": "entry", "origin_payment_id": 1}
        )
        self.assertFalse(
            AML.new(
                {"display_type": "product", "move_id": payment_move.id}
            )._check_required_analytic()
        )
        # bank statement entry (auto-generated from bank statement)
        statement_move = self.env["account.move"].new(
            {"move_type": "entry", "statement_line_id": 1}
        )
        self.assertFalse(
            AML.new(
                {"display_type": "product", "move_id": statement_move.id}
            )._check_required_analytic()
        )

        # Docline with NO display_type field (PR / EX / AV shape) -> must enforce
        self.assertNotIn(
            "display_type",
            self.env["budget.move.adjustment.item"]._fields,
            "Fixture model must have no display_type field",
        )
        budget_adjust = self.BudgetAdjust.create({"date_commit": "2001-02-01"})
        with Form(budget_adjust.adjust_item_ids) as line:
            line.adjust_id = budget_adjust
            line.adjust_type = "consume"
            line.product_id = self.product1
            line.amount = 100.0  # no analytic_distribution on purpose
        line.save()
        with self.assertRaisesRegex(UserError, "Please fill analytic account."):
            budget_adjust.action_adjust()

    @freeze_time("2001-02-01")
    def test_26_not_affect_budget_line_level(self):
        """Test line-level not_affect_budget on vendor bills.

        - Both lines with analytic -> both commit budget.
        - Line 2 marked not_affect_budget -> only line 1 commits budget.
        - Header not_affect_budget=True is master switch -> no line commits budget,
          even if a line has not_affect_budget=False.
        """
        analytic_distribution = {self.costcenter1.id: 100}

        def _add_invoice_line(bill, account, not_affect_budget=False):
            bill.write(
                {
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "quantity": 1,
                                "account_id": account.id,
                                "price_unit": 50.0,
                                "analytic_distribution": analytic_distribution,
                                "not_affect_budget": not_affect_budget,
                            }
                        )
                    ]
                }
            )

        # Case 1: Both lines commit budget.
        bill1 = self._create_simple_bill(analytic_distribution, self.account_kpi1, 50.0)
        _add_invoice_line(bill1, self.account_kpi2)
        bill1.action_post()
        self.assertEqual(bill1.state, "posted")
        self.assertTrue(all(line.can_commit for line in bill1.invoice_line_ids))
        for line in bill1.invoice_line_ids:
            self.assertEqual(len(line.budget_move_ids), 1)

        # Case 2: Line 2 not_affect_budget -> only line 1 commits budget.
        bill2 = self._create_simple_bill(analytic_distribution, self.account_kpi1, 50.0)
        _add_invoice_line(bill2, self.account_kpi2, not_affect_budget=True)
        line2_kpi1 = bill2.invoice_line_ids.filtered(
            lambda line: line.account_id == self.account_kpi1
        )
        line2_kpi2 = bill2.invoice_line_ids.filtered(
            lambda line: line.account_id == self.account_kpi2
        )
        bill2.action_post()
        self.assertEqual(bill2.state, "posted")
        self.assertTrue(line2_kpi1.can_commit)
        self.assertFalse(line2_kpi2.can_commit)
        self.assertEqual(len(line2_kpi1.budget_move_ids), 1)
        self.assertEqual(len(line2_kpi2.budget_move_ids), 0)

        # Case 3: Header not_affect_budget=True is master switch.
        # Create with header True (auto-propagates to lines), then explicitly set
        # line 2 to False. Header still wins -> no line commits budget.
        bill3 = self._create_simple_bill(analytic_distribution, self.account_kpi1, 50.0)
        _add_invoice_line(bill3, self.account_kpi2)
        bill3.write({"not_affect_budget": True})
        line3_kpi1 = bill3.invoice_line_ids.filtered(
            lambda line: line.account_id == self.account_kpi1
        )
        line3_kpi2 = bill3.invoice_line_ids.filtered(
            lambda line: line.account_id == self.account_kpi2
        )
        # Header propagation set all lines to True. Override line 2 back to False.
        line3_kpi2.write({"not_affect_budget": False})
        self.assertTrue(bill3.not_affect_budget)
        self.assertTrue(line3_kpi1.not_affect_budget)
        self.assertFalse(line3_kpi2.not_affect_budget)
        # But can_commit is driven by header, so all lines cannot commit.
        self.assertTrue(all(not line.can_commit for line in bill3.invoice_line_ids))
        bill3.action_post()
        self.assertEqual(bill3.state, "posted")
        self.assertEqual(
            sum(len(line.budget_move_ids) for line in bill3.invoice_line_ids), 0
        )
