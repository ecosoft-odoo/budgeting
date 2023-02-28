# Copyright 2023 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo.exceptions import UserError
from odoo.tests.common import Form

from odoo.addons.account_payment_multi_deduction.tests.test_payment_multi_deduction import (
    TestPaymentMultiDeduction,
)


class TestPaymentMultiDeductionActivity(TestPaymentMultiDeduction):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.activity_expense = cls.env["budget.activity"].create(
            {
                "name": "Activity Expense",
                "account_id": cls.account_expense.id,
                "company_id": cls.env.company.id,
            }
        )

    def test_01_register_payment_fully_paid(self):
        self.cust_invoice.action_post()  # total amount 450.0
        ctx = {
            "active_ids": [self.cust_invoice.id],
            "active_id": self.cust_invoice.id,
            "active_model": "account.move",
        }
        with Form(
            self.payment_register_model.with_context(**ctx),
            view=self.register_view_id,
        ) as f:
            f.amount = 400.0  # Reduce to 400.0, and mark fully paid
            f.payment_difference_handling = "reconcile"
            f.activity_id = self.activity_expense
        payment_register = f.save()
        payment_id = payment_register._create_payments()
        payment = self.payment_model.browse(payment_id.id)
        self.assertEqual(payment.state, "posted")

    def test_02_one_invoice_payment(self):
        """Validate 1 invoice and make payment with 2 deduction"""
        self.cust_invoice.action_post()  # total amount 450.0
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
                    f2.activity_id = self.activity_expense
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
                f2.activity_id = self.activity_expense
                f2.account_id = self.account_expense
                f2.name = "Expense 1"
                f2.amount = 20.0
            with f.deduction_ids.new() as f2:
                f2.activity_id = self.activity_expense
                f2.account_id = self.account_expense
                f2.name = "Expense 2"
                f2.amount = 30.0

        payment_register = f.save()
        payment_id = payment_register._create_payments()
        payment = self.payment_model.browse(payment_id.id)
        self.assertEqual(payment.state, "posted")

        move_lines = self.move_line_model.search([("payment_id", "=", payment.id)])
        bank_account = (
            payment.journal_id.company_id.account_journal_payment_debit_account_id
        )
        self.assertEqual(self.cust_invoice.payment_state, "paid")
        self.assertRecordValues(
            move_lines,
            [
                {"account_id": bank_account.id, "debit": 400.0, "credit": 0.0},
                {
                    "account_id": self.account_receivable.id,
                    "debit": 0.0,
                    "credit": 450.0,
                },
                {
                    "activity_id": self.activity_expense.id,
                    "account_id": self.account_expense.id,
                    "name": "Expense 1",
                    "debit": 20.0,
                    "credit": 0.0,
                },
                {
                    "activity_id": self.activity_expense.id,
                    "account_id": self.account_expense.id,
                    "name": "Expense 2",
                    "debit": 30.0,
                    "credit": 0.0,
                },
            ],
        )
