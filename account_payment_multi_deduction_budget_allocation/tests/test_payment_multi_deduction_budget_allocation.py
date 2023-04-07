# Copyright 2023 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo.tests.common import Form

from odoo.addons.account_payment_multi_deduction.tests.test_payment_multi_deduction import (
    TestPaymentMultiDeduction,
)
from odoo.addons.budget_allocation.tests.test_budget_allocation import (
    TestBudgetAllocation,
)


class TestPaymentMultiDeductionActivity(
    TestPaymentMultiDeduction, TestBudgetAllocation
):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_01_register_payment_fully_paid(self):
        # budget control is depends on budget allocation
        budget_control_ids = self.test_02_process_budget_allocation()
        # Test with 1 budget control, it can commit budget not over 250
        budget_control = budget_control_ids[0]
        self.assertEqual(
            sum(budget_control.allocation_line_ids.mapped("allocated_amount")), 250
        )
        budget_control.write({"template_line_ids": [self.template_line1.id]})
        # Test item created for 1 kpi x 4 quarters = 4 budget items
        budget_control.prepare_budget_control_matrix()
        assert len(budget_control.line_ids) == 4
        # Assign budget.control amount: 250
        with Form(budget_control.line_ids[0]) as line:
            line.amount = 250
        # Control budget
        budget_control.action_done()
        self.budget_period.control_budget = True

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
            f.writeoff_analytic_account_id = self.costcenterX
            f.writeoff_fund_id = self.fund1_g1
            f.writeoff_account_id = self.account_kpi1
        payment_register = f.save()
        payment_id = payment_register._create_payments()
        payment = self.payment_model.browse(payment_id.id)
        self.assertEqual(payment.state, "posted")
