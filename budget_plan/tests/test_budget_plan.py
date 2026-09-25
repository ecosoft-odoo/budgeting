# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

from freezegun import freeze_time

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.budget_control.tests.common import BudgetControlCommon


@tagged("post_install", "-at_install")
class TestBudgetPlan(BudgetControlCommon):
    @classmethod
    @freeze_time("2001-02-01")
    def setUpClass(cls):
        super().setUpClass()
        cls.BudgetPlan = cls.env["budget.plan"]
        # Create sample ready to use Budget Control
        cls.budget_control = cls.BudgetControl.create(
            {
                "name": "CostCenter1/2002",
                "template_id": cls.budget_period.template_id.id,
                "budget_period_id": cls.budget_period.id,
                "analytic_account_id": cls.costcenter1.id,
                "plan_date_range_type_id": cls.date_range_type.id,
                "template_line_ids": [
                    cls.template_line1.id,
                    cls.template_line2.id,
                    cls.template_line3.id,
                ],
            }
        )
        # Test item created for 3 kpi x 4 quarters = 12 budget items
        cls.budget_control.prepare_budget_control_matrix()
        assert len(cls.budget_control.line_ids) == 12
        # Assign budget.control amount: KPI1 = 100, KPI2=200, Total=300
        cls.budget_control.line_ids.filtered(lambda x: x.kpi_id == cls.kpi1)[:1].write(
            {"amount": 100}
        )
        cls.budget_control.line_ids.filtered(lambda x: x.kpi_id == cls.kpi2)[:1].write(
            {"amount": 200}
        )
        cls.budget_control.flush()  # Need to flush data into table, so it can be sql
        cls.budget_control.allocated_amount = 300
        cls.budget_control.action_done()

    @freeze_time("2001-02-01")
    def test_01_create_budget_plan(self):
        """
        Test normal process create budget plan
        """
        budget_plan = self.BudgetPlan.create(
            {
                "name": "Budget Plan Test {}".format(self.year),
                "budget_period_id": self.budget_period.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "analytic_account_id": self.costcenter1.id,
                            "amount": 100.0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "analytic_account_id": self.costcenterX.id,
                            "amount": 200.0,
                        },
                    ),
                ],
            }
        )
        self.assertEqual(len(budget_plan.line_ids), 2)
        self.assertEqual(budget_plan.state, "draft")
        self.assertEqual(budget_plan.total_amount, 300.0)
        # Allocated = New Budget + Forward Balance (0 here), live even in draft
        self.assertEqual(budget_plan.line_ids[0].allocated_amount, 100.0)
        self.assertFalse(budget_plan.line_ids[0].released_amount)
        self.assertEqual(budget_plan.line_ids[0].amount, 100.0)
        budget_plan.action_confirm()
        self.assertEqual(budget_plan.state, "confirm")
        # After confirm, Released follows Allocated (no Forward Balance here)
        self.assertEqual(budget_plan.line_ids[0].allocated_amount, 100.0)
        self.assertEqual(budget_plan.line_ids[0].released_amount, 100.0)
        self.assertEqual(budget_plan.line_ids[0].amount, 100.0)
        # Analytic has 1 budget control from create manual
        self.assertEqual(len(budget_plan.line_ids[0].budget_control_ids), 1)
        self.assertFalse(len(budget_plan.line_ids[1].budget_control_ids))
        # Archive budget control created before plan
        self.budget_control.active = False
        self.assertFalse(budget_plan.line_ids[0].budget_control_ids)
        # Create budget controls
        budget_plan.action_create_update_budget_control()
        self.assertEqual(len(budget_plan.line_ids[0].budget_control_ids), 1)
        self.assertEqual(len(budget_plan.line_ids[1].budget_control_ids), 1)
        # Budget count is not include active
        self.assertEqual(budget_plan.budget_control_count, 2)
        action = budget_plan.button_open_budget_control()
        self.assertEqual(action["domain"][0][2], budget_plan.budget_control_ids.ids)
        budget_plan.action_done()
        # Test update consumed amount
        self.assertEqual(budget_plan.line_ids[0].amount_consumed, 0.0)
        invoice = self._create_invoice(
            "in_invoice",
            self.vendor,
            datetime.today(),
            self.costcenter1,
            [{"account": self.account_kpi1, "price_unit": 100}],
        )
        invoice.action_post()
        budget_plan.action_update_plan()
        self.assertEqual(budget_plan.line_ids[0].amount_consumed, 100.0)
        self.assertEqual(budget_plan.state, "done")
        budget_plan.action_cancel()
        self.assertEqual(budget_plan.state, "cancel")
        budget_plan.action_draft()
        self.assertEqual(budget_plan.state, "draft")
        # Check new amount can not less than consumed amount
        budget_plan.line_ids[0].amount = 70
        with self.assertRaises(UserError):
            budget_plan.action_confirm()

    @freeze_time("2001-02-01")
    def test_02_allocated_amount_includes_forwarded_amounts(self):
        """A budget officer plans next year for a cost center that carries a
        balance forward. Allocated shows the carried amount on top of the new
        money. New Budget may be negative as long as Allocated is not."""
        next_period = self.env["budget.period"].create(
            {
                "name": "Budget for FY%s" % (self.year + 1),
                "template_id": self.budget_period.template_id.id,
                "bm_date_from": "%s-01-01" % (self.year + 1),
                "bm_date_to": "%s-12-31" % (self.year + 1),
                "plan_date_range_type_id": self.date_range_type.id,
                "control_level": "analytic_kpi",
            }
        )
        # Carry the whole available balance of CostCenter1 to next year
        forward = self.env["budget.balance.forward"].create(
            {
                "name": "Balance Forward {}".format(self.year + 1),
                "from_budget_period_id": self.budget_period.id,
                "to_budget_period_id": next_period.id,
            }
        )
        forward.get_budget_balance_forward()
        forward_line = forward.forward_line_ids.filtered(
            lambda line: line.analytic_account_id == self.costcenter1
        )
        self.assertEqual(forward_line.amount_balance, 300.0)
        forward_line.amount_balance_forward = 300.0
        forward.action_budget_balance_forward()

        budget_plan = self.BudgetPlan.create(
            {
                "name": "Budget Plan Test {}".format(self.year + 1),
                "budget_period_id": next_period.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "analytic_account_id": self.costcenter1.id,
                            "amount": 100.0,
                        },
                    )
                ],
            }
        )
        plan_line = budget_plan.line_ids
        # Allocated = Forward Balance + Forward Commit + New Budget
        self.assertEqual(plan_line.amount_forward_in, 300.0)
        self.assertEqual(plan_line.amount_forward_commit, 0.0)
        self.assertEqual(plan_line.allocated_amount, 400.0)
        self.assertEqual(budget_plan.total_amount, 400.0)

        # New Budget is the only amount the officer sets; Allocated follows it
        plan_line.amount = 50.0
        self.assertEqual(plan_line.amount_forward_in, 300.0)
        self.assertEqual(plan_line.allocated_amount, 350.0)

        # A negative New Budget is allowed when Allocated stays positive.
        plan_line.amount = -50.0
        self.assertEqual(plan_line.allocated_amount, 250.0)
        # Allocated cannot become negative.
        plan_line.amount = -350.0
        with self.assertRaises(UserError) as error:
            budget_plan.action_confirm()
        self.assertIn("Allocated cannot be negative", error.exception.args[0])
        self.assertEqual(budget_plan.state, "draft")
        with self.assertRaises(UserError):
            budget_plan.action_done()

        plan_line.amount = -50.0
        budget_plan.action_confirm()
        self.assertEqual(budget_plan.state, "confirm")
        self.assertEqual(plan_line.released_amount, 250.0)
