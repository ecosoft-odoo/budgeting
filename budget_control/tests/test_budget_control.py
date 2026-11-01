# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
from contextlib import ExitStack
from unittest.mock import patch

from freezegun import freeze_time
from psycopg2 import IntegrityError

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import Form, new_test_user, tagged
from odoo.tools import mute_logger

from ..models.analytic_plan import budget_row_key
from .common import get_budget_common_class


@tagged("post_install", "-at_install")
class TestBudgetControl(get_budget_common_class()):
    @classmethod
    @freeze_time("2001-02-01")
    def setUpClass(cls):
        super().setUpClass()

        # Budget Control 1
        cls.budget_control = cls.BudgetControl.create(
            {
                "analytic_account_id": cls.costcenter1.id,
                "budget_period_id": cls.budget_period.id,
                "allocated_amount": 2400.0,
            }
        )
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
        cls.budget_control2 = cls.BudgetControl.create(
            {
                "analytic_account_id": cls.costcenterX.id,
                "budget_period_id": cls.budget_period.id,
                "allocated_amount": 2400.0,
            }
        )
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

    def _create_lifetime_test_analytic(self, name):
        return self.Analytic.create(
            {
                "name": name,
                "plan_id": self.aa_plan1.id,
            }
        )

    def _get_lifetime_period_vals(self, name):
        return {
            "name": name,
            "template_id": self.template.id,
            "bm_date_from": f"{self.year}-01-01",
            "bm_date_to": f"{self.year + 1}-12-31",
            "plan_date_range_type_id": self.date_range_type.id,
            "control_level": "analytic_kpi",
        }

    def _create_fiscal_control(self, analytic):
        return self.BudgetControl.create(
            {
                "name": f"Fiscal Control - {analytic.name}",
                "analytic_account_id": analytic.id,
                "budget_period_id": self.budget_period.id,
                "plan_date_range_type_id": self.date_range_type.id,
                "currency_id": self.env.company.currency_id.id,
            }
        )

    def _create_next_period(self):
        return self.env["budget.period"].create(
            {
                "name": f"Budget for FY{self.year + 1}",
                "template_id": self.template.id,
                "bm_date_from": f"{self.year + 1}-01-01",
                "bm_date_to": f"{self.year + 1}-12-31",
                "plan_date_range_type_id": self.date_range_type.id,
            }
        )

    def _patch_forward_documents(self):
        """Forward lines of bill lines: their document models come from
        extension modules, e.g. purchases."""
        ForwardLine = self.env["budget.commit.forward.line"]
        documents = {"account.move.line": "Bill Line", "account.move": "Bill"}
        stack = ExitStack()
        for fname in ("res_model", "document_id", "document_number"):
            for attr, value in (
                ("selection", tuple(documents.items())),
                ("_selection", documents),
            ):
                stack.enter_context(
                    patch.object(ForwardLine._fields[fname], attr, value)
                )
        return stack

    def _create_bill_forward(self, name, period, lines, amount):
        """Forward of the bill ``lines`` to ``period``, ``amount`` each, to
        create with ``_patch_forward_documents``."""
        forward = self.CommitForward.create(
            {"name": name, "to_budget_period_id": period.id}
        )
        for doc in lines:
            vals = forward._prepare_vals_forward(doc, "account.move.line")
            for line_vals in vals:
                line_vals.update(
                    {
                        "amount_commit": amount,
                        "date_commit": "2001-02-01",
                        "document_number": f"account.move,{doc.move_id.id}",
                    }
                )
            self.env["budget.commit.forward.line"].create(vals)
        return forward

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
        bill1.action_post()
        # Budget figure of the line analytic, shown by the budget_popover widget
        popover = json.loads(bill1.invoice_line_ids.json_budget_popover)
        self.assertEqual(popover["title"], "Budget Figure")
        self.assertEqual(
            [item["name"] for item in popover["analytic"]],
            [self.costcenter1.display_name],
        )

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
            fields.Date.today(),
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

        # Budget can only move between sheets of the same currency
        eur_item = transfer.transfer_item_ids.new(
            {
                "budget_control_from_id": self.budget_control.id,
                "budget_control_to_id": self.BudgetControl.new(
                    {"currency_id": self.other_currency.id}
                ).id,
                "amount": 40.0,
            }
        )
        with self.assertRaisesRegex(UserError, "in different currencies"):
            eur_item._check_constraint_transfer()

        transfer.transfer_item_ids.write({"amount": 40.0})
        transfer.action_submit()
        self.assertEqual(transfer.state, "submit")
        with self.assertRaisesRegex(UserError, "not allowed on a budget transfer"):
            transfer.action_reverse()

        transfer.action_transfer()
        self.assertEqual(transfer.state, "transfer")
        # A done transfer is not applied twice
        with self.assertRaisesRegex(UserError, "not allowed on a budget transfer"):
            transfer.action_transfer()
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
        with self.assertRaisesRegex(UserError, "not allowed on a budget transfer"):
            transfer.action_reverse()
        self.assertFalse(self.budget_control.transfer_item_ids)
        self.assertAlmostEqual(self.budget_control.released_amount, 2400.0)
        self.assertAlmostEqual(self.budget_control.transferred_amount, 0.0)
        self.budget_control2._compute_transferred_amount()
        self.assertFalse(self.budget_control2.transfer_item_ids)
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

        # A row that also holds an account of a plan which is not budgeted
        # charges its budget analytic with the full amount
        report_plan = self.AnalyticPlan.create(
            {"name": "Report", "control_budget": False}
        )
        report_analytic = self.Analytic.create(
            {"name": "Report A", "plan_id": report_plan.id}
        )
        # Its accounts have no budget: their form hides the budget fields
        self.assertTrue(self.costcenter1.control_budget)
        self.assertFalse(report_analytic.control_budget)
        budget_adjust2 = self.BudgetAdjust.create({"date_commit": "2001-02-01"})
        with Form(budget_adjust2.adjust_item_ids) as line:
            line.adjust_id = budget_adjust2
            line.adjust_type = "consume"
            line.product_id = self.product1
            line.analytic_distribution = {
                f"{self.costcenter1.id},{report_analytic.id}": 100
            }
            line.amount = 50.0
        line.save()
        budget_adjust2.action_adjust()
        self.assertEqual(self.budget_control.amount_balance, 2250.0)

    def test_18_budget_carry_forward(self):
        """NOTE: This test is not yet implemented for budget_control"""
        budget_commit_forward = self.CommitForward.create(
            {
                "name": "Test: Budget Carry Forward",
                "to_budget_period_id": self.budget_period.id,
            }
        )
        # Only users allowed to edit the forward can collect commitments
        with self.assertRaises(AccessError):
            budget_commit_forward.with_user(self.employee)._get_budget_commit_forward(
                "account.move.line"
            )
        # The forward query only runs on supported document models
        with self.assertRaisesRegex(UserError, "does not support commitment forward"):
            budget_commit_forward._get_commit_docline("res.partner")
        # Nothing to do, as no budget_commit: the user is told so
        notification = budget_commit_forward.action_review_budget_commit()
        self.assertEqual(budget_commit_forward.state, "review")
        self.assertIn("No commitment dated before", notification["params"]["message"])

        budget_commit_forward._compute_missing_analytic()

        res = budget_commit_forward.preview_budget_commit_forward_info()
        self.assertEqual(res["context"]["default_forward_id"], budget_commit_forward.id)
        # The preview opens
        info = self.env[res["res_model"]].with_context(**res["context"]).create({})
        self.assertEqual(info.forward_id, budget_commit_forward)

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
        # Analytic figures follow the budget period given in the context
        costcenter = self.costcenter1
        self.assertEqual(
            costcenter.with_context(
                budget_period_ids=self.budget_period.ids
            ).amount_budget,
            2400.0,
        )
        self.assertEqual(
            costcenter.with_context(budget_period_ids=next_period.ids).amount_budget,
            0.0,
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
        self.assertEqual(self.budget_control.amount_balance, 2400.0)

        # Only users allowed to edit the forward can collect balances
        with self.assertRaises(AccessError):
            forward.with_user(self.employee).action_review_budget_balance()

        forward.state = "review"
        res = forward.preview_budget_balance_forward_info()
        info = self.env[res["res_model"]].with_context(**res["context"]).create({})
        self.assertEqual(
            [
                (line.analytic_account_id, line.initial_available)
                for line in info.forward_info_line_ids
            ],
            [(self.costcenter1, 30.0)],
        )
        forward.action_budget_balance_forward()
        self.assertEqual(self.budget_control.amount_balance, 2370.0)

        target_control = self.BudgetControl.create(
            {
                "analytic_account_id": self.costcenter1.id,
                "budget_period_id": next_period.id,
                "allocated_amount": 50.0,
            }
        )
        self.assertNotEqual(target_control, self.budget_control)
        self.assertEqual(target_control.amount_forward_in, 30.0)
        # The lines of a done forward keep what it carried
        with self.assertRaisesRegex(UserError, "cannot change"):
            forward_line.amount_balance = 40.0

        self.env["budget.control.line"].create(
            {
                "budget_control_id": target_control.id,
                "analytic_account_id": self.costcenter1.id,
                "date_from": next_period.bm_date_from,
                "date_to": next_period.bm_date_to,
                "amount": 50.0,
            }
        )
        self.assertEqual(self.budget_control.amount_forward_out, 30.0)
        self.assertEqual(self.budget_control.amount_balance, 2370.0)
        self.assertEqual(target_control.amount_forward_in, 30.0)
        self.assertEqual(target_control.amount_new_budget, 20.0)
        self.assertEqual(target_control.amount_budget, 50.0)
        self.assertEqual(target_control.amount_balance, 50.0)
        target_control.action_submit()
        self.assertEqual(target_control.state, "submit")

        target_monitoring = target_control.action_view_monitoring()
        self.assertIn(
            ("budget_period_id", "=", next_period.id),
            target_monitoring["domain"],
        )

        fields = ["budget_period_id", "amount_type", "amount"]
        groupby = ["budget_period_id", "amount_type"]
        source_data = MonitorReport._read_group_dataset(
            [
                ("analytic_account_id", "=", self.costcenter1.id),
                ("budget_period_id", "=", self.budget_period.id),
            ],
            fields,
            groupby,
        )
        target_data = MonitorReport._read_group_dataset(
            [
                ("analytic_account_id", "=", self.costcenter1.id),
                ("budget_period_id", "=", next_period.id),
            ],
            fields,
            groupby,
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

        # Cancellation is safe before a target Control enters workflow.
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

        forward.action_budget_balance_forward()
        self.budget_control.invalidate_recordset()
        # Source: 2400 - 500 forwarded out = 1900.
        self.assertEqual(self.budget_control.amount_forward_out, 500.0)
        self.assertEqual(self.budget_control.amount_balance, 1900.0)
        self.costcenter1.invalidate_recordset()
        self.assertEqual(self.costcenter1.amount_forward_out, 500.0)
        self.assertEqual(
            self.costcenter1.with_context(
                budget_period_ids=next_period.ids
            ).amount_forward_in,
            500.0,
        )

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
        """Forward balance to the analytic an ended analytic continues as
        tracks correctly."""
        BalanceForwardLine = self.env["budget.balance.forward.line"]
        MonitorReport = self.env["budget.monitor.report"]

        # Source analytic ends before the next period, and continues as another
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
        next_analytic = self.Analytic.create(
            {"name": "CostCenter1 Next", "plan_id": self.aa_plan1.id}
        )
        self.costcenter1.next_analytic_id = next_analytic
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
            }
        )
        self.assertEqual(forward.forward_line_ids.to_analytic_account_id, next_analytic)

        forward.action_budget_balance_forward()
        self.budget_control.invalidate_recordset()
        # Source: 2400 - 300 forwarded out = 2100.
        self.assertEqual(self.budget_control.amount_forward_out, 300.0)
        self.assertEqual(self.budget_control.amount_balance, 2100.0)
        # Build the target budget control and verify its breakdown.
        target_control = self.BudgetControl.create(
            {
                "analytic_account_id": next_analytic.id,
                "budget_period_id": next_period.id,
                "allocated_amount": 500.0,
            }
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
        target_control.invalidate_recordset()
        self.assertEqual(target_control.amount_forward_in, 300.0)
        self.assertEqual(target_control.amount_new_budget, 200.0)
        self.assertEqual(target_control.amount_budget, 500.0)

        # Monitoring keeps the signed negative ledger amount; the target analytic
        # only exposes its budget line (forward_in stays out to avoid duplicates).
        report_fields = ["amount_type", "amount"]
        groupby = ["amount_type"]
        source_data = MonitorReport._read_group_dataset(
            [
                ("analytic_account_id", "=", self.costcenter1.id),
                ("budget_period_id", "=", self.budget_period.id),
            ],
            report_fields,
            groupby,
        )
        source_amounts = {row["amount_type"]: row["amount"] for row in source_data}
        self.assertEqual(source_amounts["12_forward_out"], -300.0)
        target_data = MonitorReport._read_group_dataset(
            [
                ("analytic_account_id", "=", next_analytic.id),
                ("budget_period_id", "=", next_period.id),
            ],
            report_fields,
            groupby,
        )
        target_amounts = {row["amount_type"]: row["amount"] for row in target_data}
        self.assertNotIn("11_forward_in", target_amounts)
        self.assertEqual(target_amounts["10_budget"], 500.0)

    @freeze_time("2001-02-01")
    def test_18d_balance_forward_uses_active_fiscal_controls(self):
        """All active Fiscal controls are proposed for manager review."""
        next_period = self.env["budget.period"].create(
            {
                "name": f"Budget for FY{self.year + 1} - Carry Policy",
                "template_id": self.template.id,
                "bm_date_from": f"{self.year + 1}-01-01",
                "bm_date_to": f"{self.year + 1}-12-31",
                "plan_date_range_type_id": self.date_range_type.id,
                "control_level": "analytic_kpi",
            }
        )
        forward = self.env["budget.balance.forward"].create(
            {
                "name": "Department Carry Policy",
                "from_budget_period_id": self.budget_period.id,
                "to_budget_period_id": next_period.id,
            }
        )

        analytic_ids = {
            vals["analytic_account_id"] for vals in forward._prepare_vals_forward()
        }
        self.assertIn(self.costcenter1.id, analytic_ids)
        self.assertIn(self.costcenterX.id, analytic_ids)

        self.budget_control2.active = False
        analytic_ids = {
            vals["analytic_account_id"] for vals in forward._prepare_vals_forward()
        }
        self.assertNotIn(self.costcenterX.id, analytic_ids)

        lifetime_period = self.budget_period.copy(
            {
                "name": "Lifetime Period Cannot Be Forwarded",
                "budget_scope": "lifetime",
                "control_all_analytic_accounts": False,
                "control_analytic_account_ids": [Command.set(self.costcenter1.ids)],
            }
        )
        with self.assertRaisesRegex(ValidationError, "only supports Fiscal Periods"):
            self.env["budget.balance.forward"].create(
                {
                    "name": "Invalid Lifetime Forward",
                    "from_budget_period_id": lifetime_period.id,
                    "to_budget_period_id": next_period.id,
                }
            )

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

        # Shared analytic: no company, so every company can use it
        shared_aa = self.Analytic.create(
            {
                "name": "CC_Shared_test20",
                "plan_id": self.aa_plan1.id,
                "company_id": False,
            }
        )

        # Reuse existing budget_period;
        # company_ids empty = visible to all companies
        # Enable control_budget so check_budget() runs on post
        self.budget_period.write({"control_budget": True})

        bc_shared = self.BudgetControl.create(
            {
                "analytic_account_id": shared_aa.id,
                "budget_period_id": self.budget_period.id,
                "allocated_amount": 2400.0,
            }
        )
        self.assertEqual(len(bc_shared), 1)
        self.assertFalse(bc_shared.company_ids)  # every company may consume
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

        # Step 5: the budget is kept for Company A -> Company B is refused
        bc_shared.company_ids = [Command.set(self.env.company.ids)]
        bill_b3 = bill_b2.copy({"invoice_date": "2001-02-01"})
        bill_b3.invoice_line_ids.write(
            {"price_unit": 50, "analytic_distribution": analytic_dist}
        )
        with self.assertRaisesRegex(UserError, "is not allowed to use the budget"):
            bill_b3.action_post()
        # ...but can still return what it already committed
        bill_b2.invoice_line_ids.close_budget_move()

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
        # Posted from company A: the periods of company B still apply
        bill_b.with_company(company_a).action_post()
        self.assertEqual(bill_b.state, "posted")
        bc_b.invalidate_recordset()
        self.assertAlmostEqual(bc_b.amount_balance, 1900.0)

        # Monitoring puts each row in one period, the one of its company
        MonitorReport = self.env["budget.monitor.report"]
        for bill, period in ((bill_a1, period_a), (bill_b, period_b)):
            rows = MonitorReport.search(
                [("amount_type", "=", "80_actual"), ("reference", "=", bill.name)]
            )
            self.assertEqual(rows.budget_period_id, period)
            self.assertEqual(len(rows), 1)
        budget_rows = MonitorReport.search(
            [
                ("amount_type", "=", "10_budget"),
                ("analytic_account_id", "=", analytic_a.id),
            ]
        )
        self.assertEqual(len(budget_rows), len(bc_a.line_ids))
        self.assertEqual(budget_rows.budget_period_id, period_a)
        # A branch takes the period of its parent company
        branch_b = self.env["res.company"].create(
            {"name": "Branch B (test_21)", "parent_id": company_b.id}
        )
        self.env["account.budget.move"].create(
            {
                "date": "2001-03-01",
                "analytic_account_id": analytic_b.id,
                "account_id": account_kpi1_b.id,
                "amount_currency": 123.0,
                "debit": 123.0,
                "credit": 0.0,
                "company_id": branch_b.id,
            }
        )
        self.env.flush_all()
        rows = MonitorReport.search(
            [("amount_type", "=", "80_actual"), ("amount", "=", -123.0)]
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows.budget_period_id, period_b)

        # A shared analytic: each company checks the budget of its own period,
        # also when the lines of both are checked together
        shared = self.Analytic.create(
            {
                "name": "CC_shared_test21",
                "plan_id": self.aa_plan1.id,
                "company_id": False,
            }
        )
        for period, company, amount in (
            (period_a, company_a, 100.0),
            (period_b, company_b, 1000.0),
        ):
            control = self.BudgetControl.with_company(company).create(
                {
                    "name": f"BC_shared {company.name}",
                    "budget_period_id": period.id,
                    "analytic_account_id": shared.id,
                    "company_ids": [Command.set(company.ids)],
                    "plan_date_range_type_id": self.date_range_type.id,
                    "currency_id": company.currency_id.id,
                    "allocated_amount": amount,
                    "template_line_ids": [Command.set([self.template_line1.id])],
                    "line_ids": [
                        Command.create(
                            {
                                "date_from": "2001-01-01",
                                "date_to": "2001-12-31",
                                "template_line_id": self.template_line1.id,
                                "analytic_account_id": shared.id,
                                "amount": amount,
                            }
                        )
                    ],
                }
            )
            control.action_submit()
            control.action_done()
        bills = self.Move.browse()
        for company, journal, account in (
            (company_b, journal_b, account_kpi1_b),
            (company_a, bill_a1.journal_id, self.account_kpi1),
        ):
            bills |= self.Move.with_company(company).create(
                {
                    "move_type": "in_invoice",
                    "journal_id": journal.id,
                    "partner_id": self.vendor.id,
                    "invoice_date": "2001-02-01",
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "quantity": 1,
                                "account_id": account.id,
                                "price_unit": 200,
                                "analytic_distribution": {str(shared.id): 100},
                            }
                        )
                    ],
                }
            )
        # Company A has 100 for 200, company B 1000 for 200
        with self.assertRaisesRegex(UserError, "Budget not sufficient"):
            self.env["budget.period"].check_budget_precommit(bills.invoice_line_ids)

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
        # A line without KPI is checked against the amounts without KPI
        self.env["account.budget.move"].create(
            {
                "date": "2001-02-01",
                "analytic_account_id": self.costcenter1.id,
                "account_id": self.account_kpiX.id,
                "amount_currency": 10.0,
                "debit": 10.0,
                "credit": 0.0,
            }
        )
        with self.assertRaisesRegex(UserError, "Total amount in KPI"):
            self.budget_control.write(
                {
                    "line_ids": [
                        Command.create(
                            {
                                "date_from": "2001-01-01",
                                "date_to": "2001-03-31",
                                "analytic_account_id": self.costcenter1.id,
                                "amount": 0.0,
                            }
                        )
                    ]
                }
            )

    def test_23_check_budget_company_allowed(self):
        """Allowed companies of a budget follow its analytic's company."""
        company_a = self.env.company
        analytic = self.Analytic.create(
            {
                "name": "CC_test23",
                "plan_id": self.aa_plan1.id,
                "company_id": company_a.id,
            }
        )
        control = self._create_fiscal_control(analytic)
        self.assertEqual(control.company_ids, company_a)
        # A company analytic only serves its company and branches
        with self.assertRaisesRegex(ValidationError, "or its branches"):
            control.company_ids = [Command.set(self.company_b.ids)]
        control.company_ids = [Command.set(company_a.ids)]

        # Companies sharing a budget must use its currency
        analytic.company_id = False
        with self.assertRaisesRegex(
            UserError, "sharing a budget must use the same currency"
        ):
            control.company_ids = [Command.set([company_a.id, self.company_c.id])]

    @freeze_time("2001-02-01")
    def test_24_commit_cross_currency_blocked(self):
        """Test blocks commit when doc company currency != budget currency."""
        self.budget_period.control_budget = True
        self.budget_control.action_submit()
        self.budget_control.action_done()

        # BC is in main company currency; other_currency (EUR) must differ from it.
        self.assertNotEqual(self.budget_control.currency_id, self.other_currency)
        # Share the budget with every company, so only the currency differs
        self.costcenter1.company_id = False
        self.budget_control.company_ids = [Command.clear()]

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
        self.env.user.group_ids = [Command.link(required_group.id)]
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

    @freeze_time("2001-02-01")
    def test_27_multi_analytic_budget_check(self):
        """Every analytic used by a document must be budget checked."""
        self.budget_period.control_budget = True
        self.budget_period.control_level = "analytic"
        budget_controls = self.budget_control | self.budget_control2
        budget_controls.action_submit()
        budget_controls.action_done()

        bill = self._create_simple_bill(
            {self.costcenter1.id: 100}, self.account_kpi1, 100
        )
        second_line_vals = {
            "quantity": 1,
            "account_id": self.account_kpi1.id,
            "price_unit": 100000,
            "analytic_distribution": {self.costcenterX.id: 100},
        }
        if getattr(self, "check_plan_detail_installed", False):
            second_line_vals.update(
                {
                    "fund_id": self.fund1_g1.id,
                    "analytic_tag_ids": [Command.link(self.analytic_tag1.id)],
                }
            )
        bill.write({"invoice_line_ids": [Command.create(second_line_vals)]})

        with self.assertRaisesRegex(UserError, "Budget not sufficient"):
            bill.action_post()

    @freeze_time("2001-02-01")
    def test_28_combined_analytic_distribution_key(self):
        """A distribution row charges one budget analytic with its full
        percentage; accounts of plans without Control Budget are ignored."""
        self.budget_period.control_budget = True
        self.budget_period.control_level = "analytic"
        budget_controls = self.budget_control | self.budget_control2
        budget_controls.action_submit()
        budget_controls.action_done()
        report_plan = self.AnalyticPlan.create(
            {"name": "Report", "control_budget": False}
        )
        report_analytic = self.Analytic.create(
            {"name": "Report A", "plan_id": report_plan.id}
        )
        report_key = f"{self.costcenter1.id},{report_analytic.id}"

        # The row checks costcenter1 only, with the full amount
        bill = self._create_simple_bill({report_key: 100}, self.account_kpi1, 100000)
        grouped_analytics = {
            analytic_id
            for analytic_id, _lines in self.env[
                "budget.period"
            ]._group_doclines_by_analytic(bill.invoice_line_ids)
        }
        self.assertEqual(grouped_analytics, {self.costcenter1.id})
        with self.assertRaisesRegex(UserError, "Budget not sufficient"):
            bill.action_post()
        bill.invoice_line_ids.price_unit = 100
        bill.action_post()
        self.assertEqual(bill.budget_move_ids.analytic_account_id, self.costcenter1)
        self.assertAlmostEqual(sum(bill.budget_move_ids.mapped("debit")), 100.0)

        # Budget moves are written by the documents, read-only for users
        accountant = new_test_user(
            self.env,
            login="test_budget_accountant",
            groups="base.group_user,account.group_account_manager",
        )
        bill_acc = self._create_simple_bill(
            {self.costcenter1.id: 100}, self.account_kpi1, 10
        )
        bill_acc.with_user(accountant).action_post()
        self.assertTrue(bill_acc.budget_move_ids)
        with self.assertRaises(AccessError):
            bill_acc.budget_move_ids.with_user(accountant).unlink()
        with self.assertRaises(AccessError):
            bill_acc.budget_move_ids.with_user(accountant).write({"debit": 0.0})
        # Monitoring is for budget users
        with self.assertRaises(AccessError):
            self.env["budget.monitor.report"].with_user(accountant).search([])
        self.env["budget.monitor.report"].with_user(self.budget_user).search([])
        # Closing a budget is for budget managers
        with self.assertRaises(AccessError):
            bill_acc.invoice_line_ids.with_user(accountant).close_budget_move()
        # ...and committing for users who may change the document
        with self.assertRaises(AccessError):
            bill_acc.invoice_line_ids.with_user(self.employee).commit_budget()
        # Analytic budget figures count the whole budget, whoever reads them
        self.costcenter1.invalidate_recordset(["amount_budget"])
        self.assertEqual(self.costcenter1.with_user(accountant).amount_budget, 2400.0)

        # Budget moves and monitoring get one column per plan without Control
        # Budget, created with the plan, holding the other accounts of the row
        cost_fname = self.aa_plan1._budget_column_name()
        report_fname = report_plan._budget_column_name()
        MonitorReport = self.env["budget.monitor.report"]
        for model in (self.env["account.budget.move"], MonitorReport):
            self.assertIn(report_fname, model._fields)
            self.assertNotIn(cost_fname, model._fields)
        self.assertEqual(bill.budget_move_ids[report_fname], report_analytic)
        actual = MonitorReport._read_group(
            [("amount_type", "=", "80_actual"), (report_fname, "!=", False)],
            [report_fname],
            ["amount:sum"],
        )
        self.assertEqual(actual, [(report_analytic, -100.0)])
        # Budget rows only know their budget analytic
        budget = MonitorReport._read_group(
            [
                ("amount_type", "=", "10_budget"),
                ("analytic_account_id", "=", self.costcenter1.id),
            ],
            [report_fname],
            ["amount:sum"],
        )
        self.assertEqual(
            [report for report, _amount in budget], [report_analytic.browse()]
        )
        # The column follows Control Budget, which stays off once it is used
        extra_plan = self.AnalyticPlan.create({"name": "Extra"})
        extra_fname = extra_plan._budget_column_name()
        self.assertNotIn(extra_fname, self.env["account.budget.move"]._fields)
        extra_plan.control_budget = False
        self.assertIn(extra_fname, self.env["account.budget.move"]._fields)
        with self.assertRaisesRegex(UserError, "Control Budget cannot change"):
            report_plan.control_budget = True
        with self.assertRaisesRegex(UserError, "Control Budget cannot change"):
            self.aa_plan1.control_budget = False

        # The columns show next to the budget analytic in the views
        BudgetMove = self.env["account.budget.move"]
        for view_type in ("list", "form"):
            arch = BudgetMove.get_view(view_type=view_type)["arch"]
            self.assertIn(f'name="{report_fname}"', arch)
        search_arch = MonitorReport.get_view(view_type="search")["arch"]
        self.assertIn(f"group_by_{report_fname}", search_arch)
        bill_arch = self.Move.get_view(view_type="form")["arch"]
        self.assertIn(f'name="{report_fname}"', bill_arch)

        # Accounts and plans used on budget moves keep their root plan
        with self.assertRaisesRegex(UserError, "used on budget moves"):
            report_plan.parent_id = self.aa_plan1
        with self.assertRaisesRegex(UserError, "used on budget moves"):
            report_analytic.plan_id = self.aa_plan1
        # A budget analytic may be in several rows of a line
        bill_rows = self._create_simple_bill(
            {report_key: 60, str(self.costcenter1.id): 40}, self.account_kpi1, 100
        )
        bill_rows.action_post()
        self.assertEqual(
            sorted(bill_rows.budget_move_ids.mapped("debit")), [40.0, 60.0]
        )
        self.assertEqual(
            bill_rows.budget_move_ids.filtered(lambda move: move.debit == 60)[
                report_fname
            ],
            report_analytic,
        )

        # One row cannot charge two budgets: split it into rows instead
        both_key = f"{self.costcenter1.id},{self.costcenterX.id}"
        bill2 = self._create_simple_bill({both_key: 100}, self.account_kpi1, 100)
        with self.assertRaisesRegex(UserError, "allowed per analytic row"):
            bill2.action_post()
        bill2.invoice_line_ids.analytic_distribution = {
            report_key: 60,
            str(self.costcenterX.id): 40,
        }
        bill2.action_post()
        debits = {
            move.analytic_account_id: move.debit for move in bill2.budget_move_ids
        }
        self.assertAlmostEqual(debits[self.costcenter1], 60.0)
        self.assertAlmostEqual(debits[self.costcenterX], 40.0)
        # Committing the line alone sets the KPI of each move it creates
        moves = bill2.invoice_line_ids.commit_budget()
        self.assertEqual(moves.analytic_account_id, self.costcenter1 | self.costcenterX)
        self.assertEqual(moves.kpi_id, self.kpi1)

        # The budget rows must cover the whole line, even without budget check
        self.budget_period.control_budget = False
        bill3 = self._create_simple_bill(
            {self.costcenter1.id: 60}, self.account_kpi1, 100
        )
        with self.assertRaisesRegex(UserError, "must 100%"):
            bill3.action_post()
        # Lines that do not affect budget are not checked at all
        bill3.invoice_line_ids.write(
            {"not_affect_budget": True, "analytic_distribution": {both_key: 100}}
        )
        bill3.action_post()
        self.assertFalse(bill3.budget_move_ids)

        # Budgets stay on plans with Control Budget ticked
        control_vals = {
            "name": "Guarded budget",
            "budget_period_id": self.budget_period.id,
            "plan_date_range_type_id": self.date_range_type.id,
            "currency_id": self.env.company.currency_id.id,
        }
        with self.assertRaisesRegex(ValidationError, "Control Budget ticked"):
            self.BudgetControl.create(
                dict(control_vals, analytic_account_id=report_analytic.id)
            )
        sheet_plan = self.AnalyticPlan.create({"name": "Sheets"})
        guarded = self.Analytic.create({"name": "Guarded", "plan_id": sheet_plan.id})
        self.BudgetControl.create(dict(control_vals, analytic_account_id=guarded.id))
        with self.assertRaisesRegex(ValidationError, "must stay ticked"):
            sheet_plan.control_budget = False
        with self.assertRaisesRegex(ValidationError, "Control Budget ticked"):
            guarded.plan_id = report_plan

    @freeze_time("2001-02-01")
    def test_31_core_lifetime_setup_overrides_fiscal_period(self):
        """Core creates one multi-year budget without any Project module flow."""
        analytic = self.Analytic.create(
            {"name": "Lifetime Initiative", "plan_id": self.aa_plan1.id}
        )
        fiscal_2002 = self.budget_period.copy(
            {
                "name": "Budget for FY2002",
                "bm_date_from": "2002-01-01",
                "bm_date_to": "2002-12-31",
            }
        )
        setup_action = analytic.action_open_lifetime_budget_setup()
        self.assertEqual(setup_action["res_model"], "budget.lifetime.setup")
        setup = (
            self.env["budget.lifetime.setup"]
            .with_context(**setup_action["context"])
            .create(
                {
                    "date_from": "2001-02-01",
                    "date_to": "2002-12-31",
                    "template_id": self.template.id,
                    "plan_date_range_type_id": self.date_range_type.id,
                    "control_level": "analytic_kpi",
                    "allocated_amount": 500.0,
                }
            )
        )
        with self.assertRaisesRegex(UserError, "does not cover the complete period"):
            setup.action_create_lifetime_budget()
        analytic.invalidate_recordset(["budget_control_scope", "budget_period_id"])
        self.assertEqual(analytic.budget_control_scope, "fiscal")
        self.assertFalse(analytic.budget_period_id)

        for name, date_start, date_end in (
            ("2002/Test/Q-1", "2002-01-01", "2002-03-31"),
            ("2002/Test/Q-2", "2002-04-01", "2002-06-30"),
            ("2002/Test/Q-3", "2002-07-01", "2002-09-30"),
            ("2002/Test/Q-4", "2002-10-01", "2002-12-31"),
        ):
            self.env["date.range"].create(
                {
                    "name": name,
                    "date_start": date_start,
                    "date_end": date_end,
                    "type_id": self.date_range_type.id,
                }
            )
        control_action = setup.action_create_lifetime_budget()
        control = self.BudgetControl.browse(control_action["res_id"])
        lifetime_period = control.budget_period_id

        self.assertEqual(analytic.budget_control_scope, "lifetime")
        self.assertEqual(analytic.budget_period_id, lifetime_period)
        self.assertEqual(lifetime_period.budget_scope, "lifetime")
        self.assertEqual(lifetime_period.name, analytic.name)
        self.assertTrue(lifetime_period.control_budget)
        self.assertFalse(lifetime_period.control_all_analytic_accounts)
        self.assertEqual(lifetime_period.control_analytic_account_ids, analytic)
        self.assertEqual(control.allocated_amount, 500.0)
        self.assertEqual(len(control.line_ids), 24)
        self.assertEqual(
            min(control.line_ids.mapped("date_from")).isoformat(), "2001-02-01"
        )

        control.line_ids.unlink()
        self.env["budget.control.line"].create(
            {
                "budget_control_id": control.id,
                "analytic_account_id": analytic.id,
                "date_from": "2001-02-01",
                "date_to": "2002-12-31",
                "template_line_id": self.template_line1.id,
                "amount": 500.0,
            }
        )
        control.action_submit()
        control.action_done()

        with self.assertRaisesRegex(
            ValidationError, "already has Lifetime Budget Period"
        ):
            self.budget_period.copy(
                {
                    "name": "Duplicate Lifetime Period",
                    "budget_scope": "lifetime",
                    "control_all_analytic_accounts": False,
                    "control_analytic_account_ids": [Command.set(analytic.ids)],
                }
            )

        BudgetPeriod = self.env["budget.period"]
        self.assertEqual(
            BudgetPeriod._get_eligible_budget_period("2002-06-01"), fiscal_2002
        )
        self.assertEqual(
            BudgetPeriod.with_context(
                budget_analytic_id=analytic.id
            )._get_eligible_budget_period("2002-06-01"),
            lifetime_period,
        )

        bill = self._create_simple_bill(
            {str(analytic.id): 100}, self.account_kpi1, 400.0
        )
        bill.invoice_date = "2002-06-01"
        bill.action_post()
        control.invalidate_recordset()
        self.assertAlmostEqual(control.amount_actual, 400.0)
        self.assertAlmostEqual(control.amount_balance, 100.0)

        excessive_bill = self._create_simple_bill(
            {str(analytic.id): 100}, self.account_kpi1, 101.0
        )
        excessive_bill.invoice_date = "2002-07-01"
        with self.assertRaisesRegex(UserError, "Budget not sufficient"):
            excessive_bill.action_post()

    def test_32_lifetime_analytic_account(self):
        # Scope default and period date dependency
        analytic = self._create_lifetime_test_analytic("Fiscal Date Dependency")
        self.assertEqual(analytic.budget_control_scope, "fiscal")
        self.assertEqual(self.budget_period.budget_scope, "fiscal")

        period = self.budget_period.copy(
            {
                "name": "Fiscal Period Date Dependency",
                "bm_date_from": f"{self.year + 1}-02-01",
                "bm_date_to": f"{self.year + 1}-11-30",
            }
        )
        analytic.budget_period_id = period
        self.assertEqual(analytic.bm_date_from, period.bm_date_from)
        self.assertEqual(analytic.bm_date_to, period.bm_date_to)

        period.write(
            {
                "bm_date_from": f"{self.year + 1}-03-01",
                "bm_date_to": f"{self.year + 1}-10-31",
            }
        )
        analytic.invalidate_recordset(["bm_date_from", "bm_date_to"])
        self.assertEqual(analytic.bm_date_from, period.bm_date_from)
        self.assertEqual(analytic.bm_date_to, period.bm_date_to)

        # Create a new Lifetime Period
        analytic = self._create_lifetime_test_analytic("New Lifetime Period")
        period = analytic._create_lifetime_budget_period(
            {
                **self._get_lifetime_period_vals("New Lifetime Period"),
                "budget_scope": "fiscal",
                "control_all_analytic_accounts": True,
            }
        )

        self.assertEqual(analytic.budget_control_scope, "lifetime")
        self.assertEqual(analytic.budget_period_id, period)
        self.assertEqual(period.budget_scope, "lifetime")
        self.assertFalse(period.control_all_analytic_accounts)
        self.assertEqual(period.control_analytic_account_ids, analytic)

        # Resolve Fiscal and Lifetime Periods independently for the same date
        BudgetPeriod = self.env["budget.period"]
        scoped_period = BudgetPeriod.with_context(budget_analytic_id=analytic.id)
        self.assertEqual(
            BudgetPeriod._get_eligible_budget_period(f"{self.year}-01-15"),
            self.budget_period,
        )
        self.assertEqual(
            scoped_period._get_eligible_budget_period(f"{self.year}-06-01"),
            period,
        )
        self.assertFalse(
            scoped_period._get_eligible_budget_period(f"{self.year + 2}-01-01")
        )

        # A company-specific Lifetime Period is not eligible in another company
        period.company_ids = self.env.company
        self.assertEqual(
            scoped_period._get_eligible_budget_period(f"{self.year}-06-01"),
            period,
        )
        self.assertFalse(
            scoped_period.with_company(self.company_b)._get_eligible_budget_period(
                f"{self.year}-06-01"
            )
        )

        # Create a Lifetime Period by copying a reference period
        analytic = self._create_lifetime_test_analytic("Copied Lifetime Period")
        period = analytic._create_lifetime_budget_period(
            self._get_lifetime_period_vals("Copied Lifetime Period"),
            reference_period=self.budget_period,
        )

        self.assertNotEqual(period, self.budget_period)
        self.assertEqual(period.name, "Copied Lifetime Period")
        self.assertEqual(period.budget_scope, "lifetime")
        self.assertEqual(period.control_analytic_account_ids, analytic)
        self.assertEqual(analytic.budget_period_id, period)

        # Archived controls do not block the Lifetime setup action
        analytic = self._create_lifetime_test_analytic("Lifetime Setup Action")
        control = self._create_fiscal_control(analytic)
        control.active = False
        self.env.company.budget_template_id = self.template

        action = analytic.action_open_lifetime_budget_setup()

        self.assertEqual(action["res_model"], "budget.lifetime.setup")
        self.assertEqual(action["target"], "new")
        self.assertEqual(action["context"]["default_analytic_account_id"], analytic.id)
        self.assertEqual(action["context"]["default_name"], analytic.name)
        self.assertEqual(action["context"]["default_template_id"], self.template.id)

    def test_33_lifetime_analytic_errors(self):
        BudgetPeriod = self.env["budget.period"]
        controlled = self._create_lifetime_test_analytic("Controlled Lifetime")

        with (
            self.assertRaisesRegex(ValidationError, "start date must be before"),
            self.env.cr.savepoint(),
        ):
            BudgetPeriod.create(
                {
                    **self._get_lifetime_period_vals("Invalid Period Dates"),
                    "bm_date_from": f"{self.year + 1}-12-31",
                    "bm_date_to": f"{self.year}-01-01",
                }
            )
        with (
            self.assertRaisesRegex(ValidationError, "must be restricted to"),
            self.env.cr.savepoint(),
        ):
            BudgetPeriod.create(
                {
                    **self._get_lifetime_period_vals("Unrestricted Lifetime Period"),
                    "budget_scope": "lifetime",
                    "control_all_analytic_accounts": True,
                    "control_analytic_account_ids": [Command.set(controlled.ids)],
                }
            )
        with (
            self.assertRaisesRegex(ValidationError, "exactly one controlled analytic"),
            self.env.cr.savepoint(),
        ):
            BudgetPeriod.create(
                {
                    **self._get_lifetime_period_vals("Empty Lifetime Period"),
                    "budget_scope": "lifetime",
                    "control_all_analytic_accounts": False,
                    "control_analytic_account_ids": [Command.clear()],
                }
            )

        missing_period = self._create_lifetime_test_analytic("Missing Lifetime Period")
        with self.assertRaisesRegex(UserError, "needs its dedicated Lifetime"):
            missing_period.budget_control_scope = "lifetime"

        uncontrolled = self._create_lifetime_test_analytic("Uncontrolled Lifetime")
        other_period = BudgetPeriod.create(
            {
                **self._get_lifetime_period_vals("Other Analytic Lifetime Period"),
                "budget_scope": "lifetime",
                "control_all_analytic_accounts": False,
                "control_analytic_account_ids": [Command.set(controlled.ids)],
            }
        )
        with self.assertRaisesRegex(UserError, "must control analytic"):
            uncontrolled.write(
                {
                    "budget_control_scope": "lifetime",
                    "budget_period_id": other_period.id,
                }
            )

        lifetime_analytic = self._create_lifetime_test_analytic("Lifetime Guards")
        lifetime_analytic._create_lifetime_budget_period(
            self._get_lifetime_period_vals("Lifetime Guards")
        )
        with self.assertRaisesRegex(UserError, "already has a Lifetime Budget Period"):
            lifetime_analytic._create_lifetime_budget_period(
                self._get_lifetime_period_vals("Duplicate Lifetime")
            )
        with self.assertRaisesRegex(UserError, "already uses Lifetime budgeting"):
            lifetime_analytic.action_open_lifetime_budget_setup()

        active_analytic = self._create_lifetime_test_analytic("Active Fiscal Control")
        active_control = self._create_fiscal_control(active_analytic)
        with self.assertRaisesRegex(UserError, "Archive or cancel Budget Control"):
            active_analytic.action_open_lifetime_budget_setup()
        with self.assertRaisesRegex(UserError, "Archive or cancel Budget Control"):
            active_analytic._create_lifetime_budget_period(
                self._get_lifetime_period_vals("Blocked Lifetime")
            )

        active_lifetime_period = BudgetPeriod.create(
            {
                **self._get_lifetime_period_vals("Active Control Lifetime Period"),
                "budget_scope": "lifetime",
                "control_all_analytic_accounts": False,
                "control_analytic_account_ids": [Command.set(active_analytic.ids)],
            }
        )
        with self.assertRaisesRegex(UserError, "incompatible Budget Control"):
            active_analytic.write(
                {
                    "budget_control_scope": "lifetime",
                    "budget_period_id": active_lifetime_period.id,
                }
            )

        active_control.state = "cancel"
        active_analytic.write(
            {
                "budget_control_scope": "lifetime",
                "budget_period_id": active_lifetime_period.id,
            }
        )
        self.assertEqual(active_analytic.budget_control_scope, "lifetime")

        existing_period_analytic = self._create_lifetime_test_analytic(
            "Existing Lifetime Period"
        )
        existing_period = BudgetPeriod.create(
            {
                **self._get_lifetime_period_vals("Existing Lifetime Period"),
                "budget_scope": "lifetime",
                "control_all_analytic_accounts": False,
                "control_analytic_account_ids": [
                    Command.set(existing_period_analytic.ids)
                ],
            }
        )
        existing_period_analytic.budget_period_id = existing_period
        with self.assertRaisesRegex(UserError, "already has a Lifetime Budget Period"):
            existing_period_analytic._create_lifetime_budget_period(
                self._get_lifetime_period_vals("Duplicate Existing Lifetime")
            )

    @freeze_time("2001-02-01")
    def test_35_budget_transfer_period_balance(self):
        """A transfer cannot make a sheet negative, whatever the other periods
        of its analytic hold."""
        transfer = self._create_budget_transfer(
            budget_from=self.budget_control, budget_to=self.budget_control2, amount=40
        )
        transfer.action_submit()
        # Overspend the period by 10, and get 1000 back in another year
        for date, debit, credit in (("2001-02-01", 2410, 0), ("2002-02-01", 0, 1000)):
            self.env["account.budget.move"].create(
                {
                    "date": date,
                    "analytic_account_id": self.costcenter1.id,
                    "account_id": self.account_kpi1.id,
                    "template_line_id": self.template_line1.id,
                    "amount_currency": debit or credit,
                    "debit": debit,
                    "credit": credit,
                }
            )
        with self.assertRaisesRegex(ValidationError, "negative budget balance"):
            transfer.action_transfer()

    @freeze_time("2001-02-01")
    def test_36_period_without_control_setup(self):
        """A period without control, e.g. for budget proposals only, needs no
        budget template or plan date range."""
        period = self.env["budget.period"].create(
            {
                "name": "Budget for FY2003",
                "bm_date_from": "2003-01-01",
                "bm_date_to": "2003-12-31",
                "template_id": False,
            }
        )
        self.assertFalse(period.control_budget or period.account)
        with self.assertRaisesRegex(ValidationError, "needs a Budget Template"):
            period.control_budget = True
        # Recording budget on account alone also needs the setup
        with self.assertRaisesRegex(ValidationError, "needs a Budget Template"):
            period.account = True
        period.write(
            {
                "template_id": self.template.id,
                "plan_date_range_type_id": self.date_range_type.id,
                "control_budget": True,
            }
        )
        self.assertTrue(period.account)
        with self.assertRaisesRegex(ValidationError, "needs a Budget Template"):
            period.template_id = False
        with self.assertRaisesRegex(ValidationError, "needs a Budget Template"):
            period.plan_date_range_type_id = False
        # A plan date range in use cannot be deleted
        range_type = self.RangeType.create({"name": "Unused range type"})
        period.plan_date_range_type_id = range_type
        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"):
            range_type.unlink()

    @freeze_time("2001-02-01")
    def test_37_create_budget_control_directly(self):
        """A sheet takes its name, plan date range and currency by default."""
        analytic = self.Analytic.create(
            {"name": "Direct Sheet", "plan_id": self.aa_plan1.id}
        )
        control = self.create_budget_control(analytic, 300.0)
        self.assertEqual(control.name, f"{self.budget_period.name} :: Direct Sheet")
        self.assertEqual(control.plan_date_range_type_id, self.date_range_type)
        self.assertEqual(control.currency_id, self.env.company.currency_id)
        # 3 KPIs x 4 quarters
        self.assertEqual(len(control.line_ids), 12)
        self.assertEqual(control.released_amount, 300.0)
        # The plan table keeps the analytic and dates of the sheet
        with self.assertRaisesRegex(UserError, "has a plan table"):
            control.analytic_account_id = self.costcenterX
        with self.assertRaisesRegex(UserError, "has a plan table"):
            control.budget_period_id = self.budget_period.copy(
                {
                    "name": "Budget for FY2002",
                    "bm_date_from": "2002-01-01",
                    "bm_date_to": "2002-12-31",
                }
            )
        control.write({"analytic_account_id": analytic.id, "allocated_amount": 400})
        # A Budget User manages the sheets they create
        user_control = self.BudgetControl.with_user(self.budget_user).create(
            {
                "analytic_account_id": self.Analytic.create(
                    {"name": "User Sheet", "plan_id": self.aa_plan1.id}
                ).id,
                "budget_period_id": self.budget_period.id,
            }
        )
        self.assertEqual(user_control.assignee_ids, self.budget_user)
        self.assertEqual(user_control.name, f"{self.budget_period.name} :: User Sheet")
        self.assertFalse(control.assignee_ids)

    @freeze_time("2001-02-01")
    def test_38_budget_control_access(self):
        """Budget users only manage the sheets assigned to them."""
        control = self.budget_control.with_user(self.budget_user)
        with self.assertRaises(AccessError):
            control.line_ids[:1].amount = 1.0
        with self.assertRaises(AccessError):
            control.unlink()
        self.budget_control.assignee_ids = [Command.link(self.budget_user.id)]
        line = control.line_ids[:1]
        amount = line.amount
        line.amount = amount + 1.0
        self.assertEqual(self.budget_control.line_ids[:1].amount, amount + 1.0)
        line.amount = amount
        # A sheet in control cannot be deleted, even by its assignee
        self.budget_control.action_done()
        with self.assertRaisesRegex(UserError, "Only draft or cancelled"):
            control.unlink()
        self.budget_control.action_cancel()
        control.unlink()
        self.assertFalse(self.budget_control.exists())

    @freeze_time("2001-02-01")
    def test_39_analytic_rows_of_one_budget(self):
        """Several rows of a line charge the same budget analytic, each with
        its own percentage, other accounts and commitment."""
        self.budget_period.control_budget = True
        self.budget_period.control_level = "analytic"
        self.budget_control.action_submit()
        self.budget_control.action_done()
        fund_plan = self.AnalyticPlan.create({"name": "Fund", "control_budget": False})
        fund_a = self.Analytic.create({"name": "Fund A", "plan_id": fund_plan.id})
        fund_b = self.Analytic.create({"name": "Fund B", "plan_id": fund_plan.id})
        fund_fname = fund_plan._budget_column_name()
        key_a = budget_row_key({self.costcenter1.id, fund_a.id})
        key_b = budget_row_key({self.costcenter1.id, fund_b.id})

        # Both rows are checked together against the budget of costcenter1
        bill = self._create_simple_bill({key_a: 60, key_b: 40}, self.account_kpi1, 3000)
        with self.assertRaisesRegex(UserError, "Budget not sufficient"):
            bill.action_post()
        bill.invoice_line_ids.price_unit = 1000
        bill.action_post()
        line = bill.invoice_line_ids
        moves = {move[fund_fname]: move.debit for move in line.budget_move_ids}
        self.assertEqual(moves, {fund_a: 600.0, fund_b: 400.0})
        self.assertEqual(line.amount_commit, {key_a: 600.0, key_b: 400.0})
        self.assertEqual(
            {move._get_budget_row_key() for move in line.budget_move_ids},
            {key_a, key_b},
        )
        self.assertAlmostEqual(self.budget_control.amount_actual, 1000.0)

        # A scalar amount cannot be shared by several rows
        with self.assertRaisesRegex(UserError, "several analytic rows"):
            line.with_context(fwd_amount_commit=100.0)._prepare_commit_vals(
                reverse=True
            )
        # ...but an amount by row can
        vals = line.with_context(
            return_amount_commit={key_b: 50.0}
        )._prepare_commit_vals(reverse=True)
        self.assertEqual(
            [(v[fund_fname], v["credit"]) for v in vals], [(fund_b.id, 50.0)]
        )
        # The rows of one analytic, e.g. to return its commitment
        vals = line._prepare_commit_vals(analytic_account_id=self.costcenter1)
        self.assertEqual(len(vals), 2)

        # Commitments are carried forward by row
        forward = self.CommitForward.create(
            {"name": "Forward rows", "to_budget_period_id": self.budget_period.id}
        )
        forward_vals = forward._prepare_vals_forward(line, "account.move.line")
        self.assertEqual(
            sorted(
                (v[fund_fname], v["analytic_percent"], v["amount_commit"])
                for v in forward_vals
            ),
            [(fund_a.id, 0.6, 600.0), (fund_b.id, 0.4, 400.0)],
        )

        # An over returned row is adjusted back to zero, the others stay
        line.with_context(return_amount_commit={key_a: 700.0}).commit_budget(
            reverse=True
        )
        self.assertEqual(line.amount_commit, {key_a: 0.0, key_b: 400.0})

        # Closing reverses every row
        line.close_budget_move()
        self.assertEqual(line.amount_commit, {key_a: 0.0, key_b: 0.0})
        self.assertAlmostEqual(self.budget_control.amount_actual, 0.0)

        # Adjustments commit by row too
        adjust = self.BudgetAdjust.create(
            {
                "date_commit": "2001-02-01",
                "adjust_item_ids": [
                    Command.create(
                        {
                            "adjust_type": "consume",
                            "account_id": self.account_kpi1.id,
                            "analytic_distribution": {key_a: 70, key_b: 30},
                            "amount": 100,
                        }
                    )
                ],
            }
        )
        adjust.action_adjust()
        self.assertEqual(
            sorted(adjust.adjust_item_ids.budget_move_ids.mapped("debit")), [30.0, 70.0]
        )

        # A company uses the other accounts of the row of its own (or parents')
        fund_d = self.Analytic.create(
            {"name": "Fund D", "plan_id": fund_plan.id, "company_id": self.company_b.id}
        )
        bill3 = self._create_simple_bill(
            {f"{self.costcenter1.id},{fund_d.id}": 100}, self.account_kpi1, 10
        )
        with self.assertRaisesRegex(
            UserError, "not allowed to use the budget of Fund D"
        ):
            bill3.action_post()

        # A row holds one account of each plan
        fund_sub = self.AnalyticPlan.create(
            {"name": "Sub Fund", "parent_id": fund_plan.id}
        )
        fund_c = self.Analytic.create({"name": "Fund C", "plan_id": fund_sub.id})
        bill2 = self._create_simple_bill(
            {f"{self.costcenter1.id},{fund_a.id},{fund_c.id}": 100},
            self.account_kpi1,
            10,
        )
        with self.assertRaisesRegex(UserError, "Only one account of each plan"):
            bill2.action_post()

    @freeze_time("2001-02-01")
    def test_40_commit_forward_reverse(self):
        """Cancelling or resetting a commitment forward reverses only what its
        completion did, such as the commitments it carried. Its
        lines are reviewed in a list, and kept as they are once done."""
        bills = self._create_simple_bill(
            {self.costcenter1.id: 100}, self.account_kpi1, 100
        ) | self._create_simple_bill({self.costcenter1.id: 100}, self.account_kpi1, 100)
        bills.action_post()
        line, line2 = bills.invoice_line_ids
        fund_plan = self.AnalyticPlan.create({"name": "Fund", "control_budget": False})
        fund_a, fund_b = self.Analytic.create(
            [{"name": f"Fund {name}", "plan_id": fund_plan.id} for name in "AB"]
        )
        next_period = self._create_next_period()

        def forward(name, amount, lines=line):
            return self._create_bill_forward(name, next_period, lines, amount)

        ForwardLine = self.env["budget.commit.forward.line"]

        def carried():
            return ForwardLine._get_commit_forward_in_map(
                next_period.ids, self.costcenter1.ids
            )[next_period.id, self.costcenter1.id]

        with self._patch_forward_documents():
            done = forward("Done", 100.0)
            done.action_budget_commit_forward()
            self.assertEqual(carried(), 100.0)
            with self.assertRaisesRegex(UserError, "cannot change"):
                done.forward_line_ids.unlink()
            # Reviewed lines are searched by document, and some kept only
            reviewed = forward("Reviewed", 30.0, lines=line | line2)
            reviewed.state = "review"
            self.assertEqual(reviewed.forward_line_count, 2)
            action = reviewed.action_view_forward_lines()
            self.assertEqual(action["domain"], [("forward_id", "=", reviewed.id)])
            kept = ForwardLine.search(
                action["domain"] + [("document_name", "=", line2.move_id.display_name)]
            )
            self.assertEqual(kept.document_number, line2.move_id)
            kept.action_keep_only_selected()
            self.assertEqual(reviewed.forward_line_ids, kept)
            # The commitment can be carried to other dimensions, e.g. a fund
            self.assertFalse(kept.to_dimension_ids)
            self.assertFalse(kept.dimension_ids)
            self.assertFalse(kept.forward_changed)
            kept.to_dimension_ids = fund_a
            # Lists highlight the lines carried elsewhere than by default
            self.assertTrue(kept.forward_changed)
            self.assertEqual(
                kept._get_target_row_key(),
                budget_row_key([kept.to_analytic_account_id.id, fund_a.id]),
            )
            with self.assertRaisesRegex(ValidationError, "one account of each plan"):
                kept.to_dimension_ids = fund_a | fund_b
            # A forward never completed changed nothing
            reviewed.action_cancel()
            self.assertEqual(carried(), 100.0)
            # Resetting a completed one reverses it before its lines go
            done.action_draft()
            self.assertEqual(done.state, "draft")
            self.assertFalse(done.forward_line_ids)
            self.assertEqual(carried(), 0.0)

    @freeze_time("2001-02-01")
    def test_41_budget_settings_of_document_company(self):
        """A line takes the budget settings of its document company, not of
        the current company."""
        line = self._create_simple_bill(
            {self.costcenter1.id: 100}, self.account_kpi1, 100
        ).invoice_line_ids
        tax = self.env["account.tax"].create({"name": "Budget Tax 7", "amount": 7.0})
        self.company_c.write(
            {"budget_include_tax": True, "budget_include_tax_method": "all"}
        )
        self.env.company.budget_include_tax = False
        self.assertFalse(line.with_company(self.company_c)._taxes_included(tax))
        self.env.company.write(
            {
                "budget_include_tax": True,
                "budget_include_tax_method": "specific",
                "budget_include_tax_account": [Command.set(tax.ids)],
            }
        )
        self.assertEqual(line.with_company(self.company_c)._taxes_included(tax), tax)
        # Prices of a document in tax included mode include its taxes
        self.env.company.budget_include_tax = False
        bill = self._create_simple_bill(
            {self.costcenter1.id: 100}, self.account_kpi1, 107
        )
        bill.write(
            {
                "document_tax_mode": "tax_included",
                "invoice_line_ids": [
                    Command.update(
                        bill.invoice_line_ids.id, {"tax_ids": [Command.set(tax.ids)]}
                    )
                ],
            }
        )
        bill.action_post()
        self.assertAlmostEqual(sum(bill.budget_move_ids.mapped("debit")), 100.0)

    @freeze_time("2001-02-01")
    def test_42_commit_forward_targets(self):
        """A forward carries its lines only to analytics their documents can
        use on the forward date: checked at the preview and on completion,
        before anything changes."""
        line = self._create_simple_bill(
            {self.costcenter1.id: 100}, self.account_kpi1, 100
        ).invoice_line_ids
        line.move_id.action_post()
        next_period = self._create_next_period()
        ended, other = self.Analytic.create(
            [
                {
                    "name": "Ended",
                    "plan_id": self.aa_plan1.id,
                    "bm_date_from": "2001-01-01",
                    "bm_date_to": "2001-12-31",
                },
                {
                    "name": "Other",
                    "plan_id": self.aa_plan1.id,
                    "company_id": self.company_c.id,
                },
            ]
        )
        with self._patch_forward_documents():
            forward = self._create_bill_forward("Targets", next_period, line, 100.0)
            forward.state = "review"
            fwd_line = forward.forward_line_ids
            fwd_line.to_analytic_account_id = ended
            with self.assertRaisesRegex(UserError, "Ended cannot take commitments"):
                forward.preview_budget_commit_forward_info()
            fwd_line.to_analytic_account_id = other
            with self.assertRaisesRegex(UserError, "not of the company"):
                forward.action_budget_commit_forward()
            fwd_line.to_analytic_account_id = self.costcenter1
            forward.action_budget_commit_forward()
            self.assertEqual(forward.state, "done")

    @freeze_time("2001-02-01")
    def test_43_commit_forward_mandatory_plans(self):
        """The forward dimensions of a line take an account of each plan
        mandatory on its document."""
        line = self._create_simple_bill(
            {self.costcenter1.id: 100}, self.account_kpi1, 100
        ).invoice_line_ids
        line.move_id.action_post()
        fund_plan = self.AnalyticPlan.create({"name": "Fund", "control_budget": False})
        fund = self.Analytic.create({"name": "Fund A", "plan_id": fund_plan.id})
        fund_plan.applicability_ids = [
            Command.create({"business_domain": "bill", "applicability": "mandatory"})
        ]
        with self._patch_forward_documents():
            forward = self._create_bill_forward(
                "Mandatory", self._create_next_period(), line, 100.0
            )
            forward.state = "review"
            with self.assertRaisesRegex(UserError, "each mandatory plan"):
                forward.action_budget_commit_forward()
            forward.forward_line_ids.to_dimension_ids = fund
            forward.action_budget_commit_forward()
            self.assertEqual(forward.state, "done")

    @freeze_time("2001-02-01")
    def test_44_commit_forward_where_analytics_continue(self):
        """Reviewed lines carry their commitments where their analytics
        continue, once they do, while done forwards keep where they carried
        their lines."""
        line = self._create_simple_bill(
            {self.costcenter1.id: 100}, self.account_kpi1, 100
        ).invoice_line_ids
        line.move_id.action_post()
        next_period = self._create_next_period()
        with self._patch_forward_documents():
            done = self._create_bill_forward("Done", next_period, line, 100.0)
            done.action_budget_commit_forward()
            # The analytic now ends before the forward date
            self.costcenter1.bm_date_to = f"{self.year}-12-31"
            reviewed = self._create_bill_forward("Reviewed", next_period, line, 50.0)
            reviewed.state = "review"
            self.assertTrue(reviewed.missing_analytic)
            action = reviewed.action_continue_analytics()
            wizard = (
                self.env[action["res_model"]]
                .with_context(**action["context"])
                .create({})
            )
            self.assertEqual(wizard.line_ids.action, "extend")
            wizard.action_confirm()
            self.assertEqual(self.costcenter1.bm_date_to, next_period.bm_date_to)
            self.assertEqual(
                reviewed.forward_line_ids.to_analytic_account_id, self.costcenter1
            )
            self.assertEqual(
                done.forward_line_ids.to_analytic_account_id, self.costcenter1
            )

    @freeze_time("2001-02-01")
    def test_45_analytic_continuation(self):
        """An analytic continues in the next period as itself while it is
        open and has no Budget Period, else as the analytic it continues as:
        the wizard links the matching one, creates it, or extends a
        continuing analytic."""
        next_period = self._create_next_period()
        Continue = self.env["budget.analytic.continue"]
        yearly, matched, dated = self.Analytic.create(
            [
                {
                    "name": name,
                    "code": name,
                    "plan_id": self.aa_plan1.id,
                    "budget_period_id": self.budget_period.id,
                }
                for name in ("Yearly", "Matched")
            ]
            + [
                {
                    "name": "Dated",
                    "plan_id": self.aa_plan1.id,
                    "bm_date_from": f"{self.year}-01-01",
                    "bm_date_to": f"{self.year}-12-31",
                }
            ]
        )
        existing = self.Analytic.create(
            {
                "name": "Matched",
                "code": "Matched",
                "plan_id": self.aa_plan1.id,
                "budget_period_id": next_period.id,
            }
        )
        lifetime = self._create_lifetime_test_analytic("Lifetime")
        lifetime._create_lifetime_budget_period(
            self._get_lifetime_period_vals("Lifetime")
        )
        # Open-ended analytics continue as themselves, lifetime ones not
        self.assertEqual(
            self.costcenter1._get_forward_analytic(next_period), self.costcenter1
        )
        self.assertFalse(lifetime._get_forward_analytic(next_period))
        for analytic in yearly | matched | dated:
            self.assertFalse(analytic._get_forward_analytic(next_period))
        wizard = Continue.create(
            {
                "budget_period_id": next_period.id,
                "analytic_ids": [
                    Command.set(
                        (self.costcenter1 | lifetime | yearly | matched | dated).ids
                    )
                ],
            }
        )
        self.assertEqual(
            {
                line.analytic_account_id: (line.action, line.next_analytic_id)
                for line in wizard.line_ids
            },
            {
                yearly: ("create", self.Analytic),
                matched: ("link", existing),
                dated: ("extend", self.Analytic),
            },
        )
        wizard.action_confirm()
        self.assertEqual(yearly.next_analytic_id.name, "Yearly")
        self.assertEqual(yearly.next_analytic_id.budget_period_id, next_period)
        self.assertEqual(
            yearly._get_forward_analytic(next_period), yearly.next_analytic_id
        )
        self.assertEqual(matched._get_forward_analytic(next_period), existing)
        self.assertEqual(dated.bm_date_to, next_period.bm_date_to)
        self.assertEqual(dated._get_forward_analytic(next_period), dated)
        # Several matches leave the choice to the user
        twin = existing.copy({"name": "Matched"})
        matched.next_analytic_id = False
        wizard = Continue.create(
            {
                "budget_period_id": next_period.id,
                "analytic_ids": [Command.set(matched.ids)],
            }
        )
        self.assertFalse(wizard.line_ids.next_analytic_id)
        with self.assertRaisesRegex(UserError, "Choose the analytic"):
            wizard.action_confirm()
        wizard.line_ids.next_analytic_id = twin
        wizard.action_confirm()
        self.assertEqual(matched.next_analytic_id, twin)
        # Yearly analytics are not extended, and no analytic loops
        with self.assertRaisesRegex(UserError, "has a Budget Period"):
            yearly._extend_budget_analytic(next_period)
        with self.assertRaisesRegex(ValidationError, "cannot continue as itself"):
            twin.next_analytic_id = matched
        # A later period continues from the end of the chain, and the open
        # forward lines take it
        later_period = self.env["budget.period"].create(
            {
                "name": f"Budget for FY{self.year + 2}",
                "template_id": self.template.id,
                "bm_date_from": f"{self.year + 2}-01-01",
                "bm_date_to": f"{self.year + 2}-12-31",
                "plan_date_range_type_id": self.date_range_type.id,
            }
        )
        second = yearly.next_analytic_id
        balance = self.env["budget.balance.forward"].create(
            {
                "name": "Two periods later",
                "from_budget_period_id": self.budget_period.id,
                "to_budget_period_id": later_period.id,
            }
        )
        balance_line = self.env["budget.balance.forward.line"].create(
            {
                "forward_id": balance.id,
                "analytic_account_id": yearly.id,
                "amount_balance": 10.0,
                "amount_balance_forward": 10.0,
            }
        )
        self.assertTrue(balance.missing_analytic)
        action = balance.action_continue_analytics()
        wizard = Continue.with_context(**action["context"]).create({})
        self.assertEqual(wizard.line_ids.analytic_account_id, second)
        wizard.action_confirm()
        self.assertEqual(yearly.next_analytic_id, second)
        third = second.next_analytic_id
        self.assertEqual(third.budget_period_id, later_period)
        self.assertEqual(balance_line.to_analytic_account_id, third)

    @freeze_time("2001-02-01")
    def test_46_balance_forward_targets(self):
        """A balance forward carries its lines where their analytics continue,
        to analytics of the target period, or without Budget Period open
        then, and keeps them once done."""
        next_period = self._create_next_period()
        forward = self.env["budget.balance.forward"].create(
            {
                "name": "Balance Targets",
                "from_budget_period_id": self.budget_period.id,
                "to_budget_period_id": next_period.id,
            }
        )
        forward.action_review_budget_balance()
        line = forward.forward_line_ids.filtered(
            lambda line: line.analytic_account_id == self.costcenter1
        )
        (forward.forward_line_ids - line).unlink()
        self.assertEqual(line.to_analytic_account_id, self.costcenter1)
        self.assertFalse(line.forward_changed)
        ended = self.Analytic.create(
            {
                "name": "Ended",
                "plan_id": self.aa_plan1.id,
                "bm_date_from": f"{self.year}-01-01",
                "bm_date_to": f"{self.year}-12-31",
            }
        )
        line.to_analytic_account_id = ended
        self.assertTrue(line.forward_changed)
        with self.assertRaisesRegex(UserError, "Ended cannot take budgets"):
            forward.preview_budget_balance_forward_info()
        # A cleared forward analytic is found again by Continue Analytics
        line.to_analytic_account_id = False
        action = forward.action_continue_analytics()
        wizard = (
            self.env[action["res_model"]].with_context(**action["context"]).create({})
        )
        self.assertFalse(wizard.line_ids)
        wizard.action_confirm()
        self.assertEqual(line.to_analytic_account_id, self.costcenter1)
        res = forward.preview_budget_balance_forward_info()
        info = self.env[res["res_model"]].with_context(**res["context"]).create({})
        self.assertFalse(info.open_commitment)
        info.action_budget_balance_forward()
        self.assertEqual(forward.state, "done")
        with self.assertRaisesRegex(UserError, "cannot change"):
            line.amount_balance_forward = 0.0
        with self.assertRaisesRegex(UserError, "cannot change"):
            line.unlink()
        # Another forward of the period does not carry it again
        other = self.env["budget.balance.forward"].create(
            {
                "name": "Balance Again",
                "from_budget_period_id": self.budget_period.id,
                "to_budget_period_id": next_period.id,
                "company_ids": [Command.set(self.env.company.ids)],
            }
        )
        other.action_review_budget_balance()
        self.assertNotIn(self.costcenter1, other.forward_line_ids.analytic_account_id)
        self.env["budget.balance.forward.line"].create(
            {
                "forward_id": other.id,
                "analytic_account_id": self.costcenter1.id,
                "amount_balance": 1.0,
                "amount_balance_forward": 1.0,
            }
        )
        with self.assertRaisesRegex(UserError, "already carries"):
            other.action_budget_balance_forward()
        with self.assertRaisesRegex(UserError, "cannot change"):
            other.forward_line_ids[:1].forward_id = forward

    def test_47_plan_date_range_coverage(self):
        """The plan table is reset only with date ranges for its whole period."""
        next_period = self._create_next_period()
        year = self.year + 1
        for quarter, (start, end) in enumerate(
            (("01-01", "03-31"), ("04-01", "06-30"), ("07-01", "09-30")), 1
        ):
            self.env["date.range"].create(
                {
                    "name": f"{year}/Test/Q-{quarter}",
                    "date_start": f"{year}-{start}",
                    "date_end": f"{year}-{end}",
                    "type_id": self.date_range_type.id,
                }
            )
        with self.assertRaisesRegex(UserError, f"starting on {year}-10-01"):
            self.create_budget_control(self.costcenter1, period=next_period)
        last_quarter = self.env["date.range"].create(
            {
                "name": f"{year}/Test/Q-4",
                "date_start": f"{year}-10-01",
                "date_end": f"{year}-12-31",
                "type_id": self.date_range_type.id,
            }
        )
        control = self.create_budget_control(self.costcenter1, period=next_period)
        lines = control.line_ids
        self.assertEqual(len(lines.date_range_id), 4)
        # A missing range keeps the plan table
        last_quarter.active = False
        with self.assertRaisesRegex(UserError, "does not cover the complete period"):
            control.prepare_budget_control_matrix()
        self.assertEqual(control.line_ids, lines)

    def test_48_monitoring_amount_type_order(self):
        """The monitoring shows commitments before actuals, whatever the order
        modules add their sources in."""
        Monitor = self.env["budget.monitor.report"]
        sources = Monitor._get_consumed_sources() + [
            {"model": ("account.move", "Test"), "type": ("30_test_commit", "Test")}
        ]
        with patch.object(type(Monitor), "_get_consumed_sources", lambda _: sources):
            keys = Monitor._fields["amount_type"].get_values(self.env)
        self.assertEqual(keys, sorted(keys))
        self.assertEqual(keys[-2:], ["30_test_commit", "80_actual"])
