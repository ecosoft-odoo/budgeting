# Copyright 2023 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import Command
from odoo.tests import tagged

from odoo.addons.budget_plan_detail.tests.test_budget_plan_detail import (
    TestBudgetPlanDetail,
)


@tagged("post_install", "-at_install")
class TestPaymentMultiDeductionBudget(TestBudgetPlanDetail):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create same analytic, difference fund, difference analytic tags
        # line 1: Costcenter1, Fund1, Tag1, 600.0
        # line 2: Costcenter1, Fund1, Tag2, 600.0
        # line 3: Costcenter1, Fund2, Tag1, 600.0
        # line 4: Costcenter1, Fund2,     , 600.0
        # line 5: CostcenterX, Fund1, Tag1, 600.0
        # line 6: CostcenterX, Fund2, Tag1, 600.0
        # line 7: CostcenterX, Fund2, Tag2, 600.0
        # line 8: CostcenterX, Fund1,     , 600.0
        cls._create_budget_plan_line_detail(cls, cls.budget_plan)
        cls.budget_plan.action_confirm_plan_detail()
        cls.budget_plan.action_confirm()
        cls.budget_plan.action_create_update_budget_control()
        cls.budget_plan.action_done()

        # Refresh data and Prepare budget control
        cls.budget_plan.invalidate_recordset()
        # Get 1 budget control, Costcenter1 has 4 plan detail
        budget_control = cls.budget_plan.budget_control_ids[0]
        budget_control.template_line_ids = [
            cls.template_line1.id,
            cls.template_line2.id,
            cls.template_line3.id,
        ]

        # Test item created for 3 kpi x 4 quarters = 12 budget items
        budget_control.prepare_budget_control_matrix()
        assert len(budget_control.line_ids) == 12
        # Costcenter1 has 3 plan detail
        # Assign budget.control amount: KPI1 = 1500, 500, 400
        bc_items = budget_control.line_ids.filtered(lambda x: x.kpi_id == cls.kpi1)
        bc_items[0].write({"amount": 1500})
        bc_items[1].write({"amount": 500})
        bc_items[2].write({"amount": 400})

        # Control budget
        budget_control.action_submit()
        budget_control.action_done()
        cls.budget_period.control_budget = True

    def test_01_one_invoice_payment_fully_paid(self):
        """Validate 1 invoice and make payment with Mark as fully paid"""
        analytic_distribution = {self.costcenter1.id: 100}
        bill1 = self._create_simple_bill(
            analytic_distribution, self.account_kpi1, 450.0
        )
        bill1.invoice_line_ids.write({"fund_id": self.fund1_g1.id})
        bill1.action_post()

        wizard = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=bill1.ids)
            .create(
                {
                    "payment_date": "2015-12-31",
                    "amount": 400.0,
                    "payment_difference_handling": "reconcile",
                }
            )
        )

        self.assertFalse(wizard.writeoff_analytic_tag_all)
        self.assertFalse(wizard.writeoff_fund_all)
        wizard._update_vals_deduction(bill1.line_ids)
        self.assertEqual(len(wizard.writeoff_analytic_tag_all), 2)
        self.assertEqual(len(wizard.writeoff_fund_all), 2)

        # Test change analytic account.
        # Fund still empty because value more than 1
        wizard._onchange_budget_all()
        self.assertFalse(wizard.writeoff_fund_id)

        wizard.write(
            {
                "writeoff_account_id": self.account_kpi1.id,
                "writeoff_fund_id": wizard.writeoff_fund_all[0].id,
                "writeoff_analytic_tag_ids": [
                    Command.set(wizard.writeoff_analytic_tag_all[0].ids)
                ],
            }
        )
        payment = wizard._create_payments()
        self.assertEqual(payment.state, "paid")

        writeoff = payment.move_id.line_ids.filtered(lambda line: line.is_writeoff)
        self.assertEqual(len(writeoff), 1)
        self.assertEqual(writeoff.fund_id, wizard.writeoff_fund_all[0])
        self.assertEqual(writeoff.analytic_tag_ids, wizard.writeoff_analytic_tag_all[0])

    def test_02_one_invoice_payment_multi_deduction(self):
        analytic_distribution = {self.costcenter1.id: 100}
        bill1 = self._create_simple_bill(
            analytic_distribution, self.account_kpi1, 450.0
        )
        bill1.invoice_line_ids.write({"fund_id": self.fund1_g1.id})
        bill1.action_post()

        wizard = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=bill1.ids)
            .create(
                {
                    "payment_date": "2015-12-31",
                    "amount": 400.0,
                    "payment_difference_handling": "reconcile_multi_deduct",
                    "deduction_ids": [
                        Command.create(
                            {
                                "account_id": self.account_kpi1.id,
                                "name": "Expense 1",
                                "amount": 20.0,
                            }
                        ),
                        Command.create(
                            {
                                "account_id": self.account_kpi1.id,
                                "name": "Expense 2",
                                "amount": 30.0,
                            }
                        ),
                    ],
                }
            )
        )

        deduction = wizard.deduction_ids
        for ded in deduction:
            self.assertFalse(ded.writeoff_fund_all)
            self.assertFalse(ded.writeoff_analytic_tag_all)
            ded.analytic_distribution = {self.costcenter1.id: 100}
            ded._onchange_budget_all()
            self.assertEqual(len(ded.writeoff_fund_all), 2)
            self.assertEqual(len(ded.writeoff_analytic_tag_all), 2)
            self.assertFalse(ded.writeoff_fund_id)
            self.assertFalse(ded.writeoff_analytic_tag_ids)
            ded.write(
                {
                    "writeoff_fund_id": ded.writeoff_fund_all[0].id,
                    "writeoff_analytic_tag_ids": [
                        Command.set(ded.writeoff_analytic_tag_all[0].ids)
                    ],
                }
            )

        payment = wizard._create_payments()
        self.assertEqual(payment.state, "paid")

        writeoff = payment.move_id.line_ids.filtered(lambda line: line.is_writeoff)
        self.assertEqual(len(writeoff), 2)
        self.assertEqual(
            writeoff[0].fund_id, wizard.deduction_ids[0].writeoff_fund_all[0]
        )
        self.assertEqual(
            writeoff[0].analytic_tag_ids,
            wizard.deduction_ids[0].writeoff_analytic_tag_all[0],
        )
