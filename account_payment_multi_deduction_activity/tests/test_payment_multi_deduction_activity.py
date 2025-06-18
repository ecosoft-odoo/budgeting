# Copyright 2023 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo.exceptions import UserError
from odoo.tests import Form, tagged

from odoo.addons.account_payment_multi_deduction.tests.test_payment_multi_deduction import (  # noqa: E501
    TestPaymentMultiDeduction,
)
from odoo.addons.budget_activity.tests.test_budget_activity import TestBudgetActivity


@tagged("post_install", "-at_install")
class TestPaymentMultiDeductionActivity(TestPaymentMultiDeduction, TestBudgetActivity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Add permission budget control on accountman
        cls.env.user.groups_id += cls.env.ref(
            "budget_control.group_budget_control_user"
        )

        # accountman can't create activity.
        # So, we add sudo() to create activity with same company
        cls.activity_diff = (
            cls.env["budget.activity"]
            .sudo()
            .create(
                {
                    "name": "Activity Diff",
                    "kpi_id": cls.kpi1.id,
                    "account_id": cls.account_expense.id,
                }
            )
        )

    def test_01_one_invoice_payment_fully_paid(self):
        """Validate 1 invoice and make payment with Mark as fully paid"""
        ctx = {
            "active_ids": [self.cust_invoice.id],
            "active_id": self.cust_invoice.id,
            "active_model": "account.move",
        }

        with Form(
            self.payment_register_model.with_context(**ctx),
            view=self.register_view_id,
        ) as f:
            f.amount = 400.0
            f.payment_difference_handling = "reconcile"
            f.writeoff_account_id = self.account_expense
        payment_register = f.save()
        payment = payment_register._create_payments()
        self.assertEqual(payment.state, "paid")

        writeoff = payment.move_id.line_ids.filtered(lambda line: line.is_writeoff)
        self.assertEqual(len(writeoff), 1)
        self.assertEqual(writeoff.account_id, self.account_expense)

    def test_02_one_invoice_payment_fully_paid_with_activity(self):
        """Validate 1 invoice and make payment with Mark as fully paid"""
        ctx = {
            "active_ids": [self.cust_invoice.id],
            "active_id": self.cust_invoice.id,
            "active_model": "account.move",
        }

        with Form(
            self.payment_register_model.with_context(**ctx),
            view=self.register_view_id,
        ) as f:
            f.amount = 400.0
            f.payment_difference_handling = "reconcile"
            f.activity_id = self.activity_diff
        payment_register = f.save()
        payment = payment_register._create_payments()
        self.assertEqual(payment.state, "paid")

        writeoff = payment.move_id.line_ids.filtered(lambda line: line.is_writeoff)
        self.assertEqual(len(writeoff), 1)
        self.assertEqual(writeoff.account_id, self.account_expense)

    def test_03_one_invoice_payment_multi_deduction_with_activity(self):
        """Validate 1 invoice and make payment with 2 deduction"""
        ctx = {
            "active_ids": [self.cust_invoice.id],
            "active_id": self.cust_invoice.id,
            "active_model": "account.move",
        }
        with self.assertRaises(UserError):  # Deduct only 20.0, throw error
            with Form(
                self.payment_register_model.with_context(**ctx),
                view=self.register_view_id,
            ) as f:
                f.amount = 400.0
                f.payment_difference_handling = "reconcile_multi_deduct"
                with f.deduction_ids.new() as f2:
                    f2.activity_id = self.activity_diff
                    f2.account_id = self.account_expense
                    f2.name = "Expense 1"
                    f2.amount = 20.0
            f.save()
        with Form(
            self.payment_register_model.with_context(**ctx),
            view=self.register_view_id,
        ) as f:
            f.amount = 400.0  # Reduce to 400.0, and mark fully paid (multi)
            f.payment_difference_handling = "reconcile_multi_deduct"
            with f.deduction_ids.new() as f2:
                f2.activity_id = self.activity_diff
                f2.account_id = self.account_expense
                f2.name = "Expense 1"
                f2.amount = 20.0
            with f.deduction_ids.new() as f2:
                f2.activity_id = self.activity_diff
                f2.account_id = self.account_expense
                f2.name = "Expense 2"
                f2.amount = 30.0

        payment_register = f.save()
        payment = payment_register._create_payments()
        self.assertEqual(payment.state, "paid")
        self.assertEqual(self.cust_invoice.payment_state, "paid")

        writeoff = payment.move_id.line_ids.filtered(lambda line: line.is_writeoff)
        self.assertEqual(len(writeoff), 2)
        self.assertEqual(writeoff.mapped("activity_id"), self.activity_diff)
