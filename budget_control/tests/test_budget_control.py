# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

from freezegun import freeze_time

from odoo import Command
from odoo.exceptions import UserError
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
