# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from json import loads

from freezegun import freeze_time

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import Form

from odoo.addons.budget_control.tests.common import BudgetControlCommon


@tagged("post_install", "-at_install")
class TestBudgetAllocation(BudgetControlCommon):
    @classmethod
    @freeze_time("2001-02-01")
    def setUpClass(cls):
        super().setUpClass()
        cls.AllocationLine = cls.env["budget.allocation.line"]
        cls.AnalyticAccount = cls.env["account.analytic.account"]
        cls.AnalyticDimension = cls.env["account.analytic.dimension"]
        cls.AnalyticTag = cls.env["account.analytic.tag"]
        cls.BudgetAllocation = cls.env["budget.allocation"]  # Create sample allocation
        cls.BudgetFund = cls.env["budget.source.fund"]
        cls.BudgetFundGroup = cls.env["budget.source.fund.group"]
        cls.BudgetPlan = cls.env["budget.plan"]
        cls.BudgetTransfer = cls.env["budget.transfer"]
        cls.costcenter1.write({"budget_period_id": cls.budget_period.id})
        cls.costcenterX.write({"budget_period_id": cls.budget_period.id})
        # Create fund
        cls.fund_group1 = cls.BudgetFundGroup.create({"name": "Test FG 1"})
        cls.fund_group2 = cls.BudgetFundGroup.create({"name": "Test FG 2"})

        cls.fund1_g1 = cls.BudgetFund.create(
            {"name": "Test Fund 1", "fund_group_id": cls.fund_group1.id}
        )
        cls.fund2_g1 = cls.BudgetFund.create(
            {"name": "Test Fund 2", "fund_group_id": cls.fund_group1.id}
        )
        cls.fund3_g2 = cls.BudgetFund.create(
            {"name": "Test Fund 3", "fund_group_id": cls.fund_group2.id}
        )
        # Config analytic tags
        cls.env.user.write(
            {
                "groups_id": [
                    (4, cls.env.ref("analytic.group_analytic_tags").id),
                ],
            }
        )
        # Create dimensions
        cls.tag_dimension1 = cls.AnalyticDimension.create(
            {"name": "Test New Dimension1", "code": "test_dimension1"}
        )
        cls.analytic_tag1 = cls.AnalyticTag.create(
            {"name": "Test Tags 1", "analytic_dimension_id": cls.tag_dimension1.id}
        )
        cls.analytic_tag2 = cls.AnalyticTag.create(
            {"name": "Test Tags 2", "analytic_dimension_id": cls.tag_dimension1.id}
        )

    def _create_budget_allocation(self, amount):
        """Create same analytic, difference fund, difference analytic tags
        line 1: Costcenter1, Fund1, Tag1, 100.0
        line 2: Costcenter1, Fund1, Tag2, 100.0
        line 3: Costcenter1, Fund2,     , 100.0
        line 4: CostcenterX, Fund1,     , 100.0
        """
        budget_allocation_id = self.BudgetAllocation.create(
            {
                "name": "Budget Allocation {}".format(self.budget_period.display_name),
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "analytic_account_id": self.costcenter1.id,
                            "fund_id": self.fund1_g1.id,
                            "analytic_tag_ids": [(4, self.analytic_tag1.id)],
                            "allocated_amount": amount,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "analytic_account_id": self.costcenter1.id,
                            "fund_id": self.fund1_g1.id,
                            "analytic_tag_ids": [(4, self.analytic_tag2.id)],
                            "allocated_amount": amount,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "analytic_account_id": self.costcenter1.id,
                            "fund_id": self.fund2_g1.id,
                            "allocated_amount": amount,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "analytic_account_id": self.costcenterX.id,
                            "fund_id": self.fund1_g1.id,
                            "allocated_amount": amount,
                        },
                    ),
                ],
            }
        )
        return budget_allocation_id

    def test_01_master_data_source_fund(self):
        self.assertEqual(self.fund1_g1.name, "Test Fund 1")
        self.fund1_g1_copy = self.fund1_g1.copy()
        self.assertEqual(self.fund1_g1_copy.name, "Test Fund 1 (copy)")

    @freeze_time("2001-02-01")
    def test_02_process_budget_allocation(self):
        amount = 100.0
        budget_allocation_id = self._create_budget_allocation(amount)
        self.assertEqual(budget_allocation_id.budget_period_id, self.budget_period)
        self.assertEqual(
            sum(budget_allocation_id.line_ids.mapped("allocated_amount")),
            budget_allocation_id.allocated_amount,
        )
        self.assertEqual(
            sum(budget_allocation_id.line_ids.mapped("released_amount")),
            0.0,
        )
        self.assertEqual(
            sum(budget_allocation_id.line_ids.mapped("estimated_amount")),
            400.0,  # following allocated
        )
        # Open Analytic with depend on date period, Check count analytic
        analytic_dict = budget_allocation_id.button_open_analytic()
        analytic_all = self.AnalyticAccount.search(analytic_dict["domain"])
        analytic_check = self.AnalyticAccount.search(
            [
                (
                    "bm_date_to",
                    ">=",
                    budget_allocation_id.budget_period_id.bm_date_from,
                ),
                (
                    "bm_date_from",
                    "<=",
                    budget_allocation_id.budget_period_id.bm_date_to,
                ),
            ]
        )
        self.assertEqual(analytic_all, analytic_check)
        budget_allocation_id.action_cancel()
        self.assertEqual(budget_allocation_id.state, "cancel")
        budget_allocation_id.action_draft()
        self.assertEqual(budget_allocation_id.state, "draft")
        budget_allocation_id.action_done()
        self.assertEqual(budget_allocation_id.state, "done")
        # After done, amount released must be equal allocated
        self.assertEqual(
            sum(budget_allocation_id.line_ids.mapped("released_amount")),
            sum(budget_allocation_id.line_ids.mapped("allocated_amount")),
        )
        # budget plan created by button done.
        self.assertTrue(budget_allocation_id.plan_id)
        # Check smart button link and plan_id must be equal.
        plan_dict = budget_allocation_id.button_open_budget_plan()
        plan = self.BudgetPlan.browse(plan_dict["res_id"])
        plan_id = budget_allocation_id.plan_id
        self.assertEqual(plan, plan_id)
        self.assertEqual(plan_id.init_amount, budget_allocation_id.allocated_amount)
        # Check case edit amount in budget allocation.
        budget_allocation_id.action_draft()
        with Form(budget_allocation_id.line_ids[0]) as f:
            f.allocated_amount = 50.0
        self.assertEqual(budget_allocation_id.allocated_amount, 350.0)
        # Initial Amount in Budget Plan and
        # Total Amount in Budget Allocation must be equal after state = done
        self.assertNotEqual(plan_id.init_amount, budget_allocation_id.allocated_amount)
        self.assertEqual(plan_id.init_amount, plan_id.total_amount)
        budget_allocation_id.action_done()
        self.assertEqual(plan_id.init_amount, budget_allocation_id.allocated_amount)
        self.assertEqual(plan_id.init_amount, plan_id.total_amount)
        self.assertEqual(plan_id.state, "draft")
        # Test cancel budget plan, allocation will change state to draft
        self.assertEqual(budget_allocation_id.state, "done")
        plan_id.unlink()
        self.assertEqual(budget_allocation_id.state, "draft")
        budget_allocation_id.action_done()
        plan_id = budget_allocation_id.plan_id
        # Check case edit amount in budget plan, not equal budget allocation.
        with self.assertRaises(UserError):
            plan_id.line_ids[0].amount = amount
            plan_id.action_confirm()
        plan_id.action_confirm()
        self.assertEqual(plan_id.state, "confirm")
        # Check budget control and plan line must be the same.
        plan_id.action_create_update_budget_control()
        self.assertEqual(len(plan_id.line_ids), len(plan_id.budget_control_ids))
        plan_id.action_done()
        self.assertEqual(plan_id.state, "done")
        budget_control_ids = plan_id.budget_control_ids
        self.assertEqual(
            budget_control_ids.mapped("allocation_line_ids"),
            budget_allocation_id.line_ids,
        )
        return budget_control_ids

    @freeze_time("2001-02-01")
    def test_02_commitment_bill(self):
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
        # Commit actual without allocation (no fund, no tags)
        bill1 = self._create_simple_bill(self.costcenter1, self.account_kpi1, 120)
        with self.assertRaises(UserError):
            bill1.action_post()
        bill1.invoice_line_ids.fund_id = self.fund1_g1.id
        bill1.invoice_line_ids.analytic_tag_ids = [(4, self.analytic_tag1.id)]
        # Fund1, Tag1 allocated 50.0, actual 120.0 it should error spend over limit
        with self.assertRaises(UserError):
            bill1.action_post()
        # KPI commit less than allocated amount.
        bill2 = self._create_simple_bill(self.costcenter1, self.account_kpi1, 40)
        bill2.invoice_line_ids.fund_id = self.fund1_g1.id
        bill2.invoice_line_ids.analytic_tag_ids = [(4, self.analytic_tag1.id)]
        bill2.action_post()
        # KPI commit 40 already, it can commit not over 10
        bill3 = self._create_simple_bill(self.costcenter1, self.account_kpi1, 30)
        bill3.invoice_line_ids.fund_id = self.fund1_g1.id
        bill3.invoice_line_ids.analytic_tag_ids = [(4, self.analytic_tag1.id)]
        with self.assertRaises(UserError):
            bill3.action_post()

    @freeze_time("2001-02-01")
    def test_03_transfer_budget_control(self):
        # budget control is depends on budget allocation
        budget_control_ids = self.test_02_process_budget_allocation()
        # add amount in all budget control
        for budget_control in budget_control_ids:
            budget_control.write({"template_line_ids": [self.template_line1.id]})
            budget_control.prepare_budget_control_matrix()
            with Form(budget_control.line_ids[0]) as line:
                line.amount = budget_control.diff_amount
        self.assertEqual(budget_control_ids[0].diff_amount, 0.0)
        self.assertEqual(budget_control_ids[1].diff_amount, 0.0)
        # Create budget transfer from
        # line 1: Costcenter1, Fund1, Tag1,  50.0 to
        # line 4: CostcenterX, Fund1,     , 100.0
        transfer = self.BudgetTransfer.create({})
        with Form(transfer.transfer_item_ids) as line:
            line.transfer_id = transfer
            line.budget_control_from_id = budget_control_ids[0]
            line.fund_from_id = self.fund1_g1
            line.budget_control_to_id = budget_control_ids[1]
            line.fund_to_id = self.fund1_g1
        transfer_line = line.save()
        transfer_line.amount = 500.0
        # no allocated in lines with no tags
        self.assertEqual(len(transfer_line.allocation_line_from_ids), 0)
        self.assertEqual(transfer_line.amount_from_available, 0)
        self.assertEqual(len(transfer_line.allocation_line_to_ids), 1)
        self.assertEqual(transfer_line.amount_to_available, 100)
        # NOTE: Test without sequence dimension, we will add it later
        self.assertFalse(transfer_line.domain_tag_from_ids)
        self.assertFalse(transfer_line.domain_tag_to_ids)
        self.assertEqual(len(transfer.transfer_item_ids), 1)
        # Add tags in budget from
        transfer_line.analytic_tag_from_ids = self.analytic_tag1
        self.assertEqual(len(transfer_line.allocation_line_from_ids), 1)
        self.assertEqual(transfer_line.amount_from_available, 50)
        # Can't transfer amount more than amount_from_available (50)
        with self.assertRaises(UserError):
            transfer.action_submit()
        transfer_line.amount = 30.0
        transfer.action_submit()
        transfer.action_transfer()
        self.assertEqual(budget_control_ids[0].diff_amount, -30.0)
        self.assertEqual(budget_control_ids[1].diff_amount, 30.0)
        transfer.action_reverse()
        self.assertEqual(budget_control_ids[0].diff_amount, 0.0)
        self.assertEqual(budget_control_ids[1].diff_amount, 0.0)

    @freeze_time("2001-02-01")
    def test_04_forward_balance_vs_init_amount(self):
        """Budget Allocation's Initial Amount only knows about newly
        allocated funds, not Forward Balance. The plan's Initial Amount
        check must therefore compare against New Budget only (not the
        Forward-Balance-inclusive Total Amount), or confirming a plan with
        any carried-forward balance would always fail."""
        prev_period = self.env["budget.period"].create(
            {
                "name": "Budget for FY Prev",
                "template_id": self.template.id,
                "bm_date_from": "%s-01-01" % (self.year - 1),
                "bm_date_to": "%s-12-31" % (self.year - 1),
                "plan_date_range_type_id": self.date_range_type.id,
                "control_level": "analytic_kpi",
            }
        )
        forward = self.env["budget.balance.forward"].create(
            {
                "name": "Test Forward for Allocation",
                "from_budget_period_id": prev_period.id,
                "to_budget_period_id": self.budget_period.id,
            }
        )
        self.env["budget.balance.forward.line"].create(
            {
                "forward_id": forward.id,
                "analytic_account_id": self.costcenter1.id,
                "amount_balance": 60.0,
                "amount_balance_forward": 60.0,
            }
        )
        forward.action_budget_balance_forward()
        self.assertEqual(forward.state, "done")

        budget_allocation_id = self._create_budget_allocation(100)
        budget_allocation_id.action_done()
        plan_id = budget_allocation_id.plan_id
        line_cc1 = plan_id.line_ids.filtered(
            lambda line: line.analytic_account_id == self.costcenter1
        )
        # New Budget from allocation only (300), Forward Balance kept apart
        self.assertEqual(line_cc1.amount, 300.0)
        self.assertEqual(line_cc1.amount_forward_in, 60.0)
        self.assertEqual(line_cc1.allocated_amount, 360.0)

        self.assertEqual(plan_id.init_amount, 400.0)
        self.assertEqual(plan_id.total_new_budget, 400.0)
        # Total Amount includes Forward Balance, so it legitimately diverges
        # from Initial Amount once a forward balance exists.
        self.assertEqual(plan_id.total_amount, 460.0)

        # Must not raise: the check compares init_amount to total_new_budget
        plan_id.action_confirm()
        self.assertEqual(plan_id.state, "confirm")

    @freeze_time("2001-02-01")
    def test_05_budget_figure_popover(self):
        """Before building any budget plan, a budget officer hovers the Budget
        Figure on an allocation line and sees what that cost center will really
        have for the period: what was carried forward, what this allocation
        adds across all its funds, and the total - which must be exactly what
        the budget plan ends up allocating. Cancelling the allocation drops its
        contribution to zero."""
        forward = self.env["budget.balance.forward"].create(
            {
                "name": "Test Forward for Budget Figure",
                "from_budget_period_id": self.env["budget.period"]
                .create(
                    {
                        "name": "Budget for FY Prev (Figure)",
                        "template_id": self.template.id,
                        "bm_date_from": "%s-01-01" % (self.year - 1),
                        "bm_date_to": "%s-12-31" % (self.year - 1),
                        "plan_date_range_type_id": self.date_range_type.id,
                        "control_level": "analytic_kpi",
                    }
                )
                .id,
                "to_budget_period_id": self.budget_period.id,
            }
        )
        self.env["budget.balance.forward.line"].create(
            {
                "forward_id": forward.id,
                "analytic_account_id": self.costcenter1.id,
                "amount_balance": 60.0,
                "amount_balance_forward": 60.0,
            }
        )
        forward.action_budget_balance_forward()

        # CostCenter1 gets 3 lines of 100 across 2 funds, CostCenterX gets 1
        budget_allocation_id = self._create_budget_allocation(100)
        line_cc1 = budget_allocation_id.line_ids.filtered(
            lambda line: line.analytic_account_id == self.costcenter1
        )[:1]
        popover = loads(line_cc1.json_budget_popover)
        self.assertEqual(popover["analytic"], self.costcenter1.display_name)
        self.assertEqual(popover["forward_in"], "60.00")
        self.assertEqual(popover["forward_commit"], "0.00")
        # Allocated is the analytic's whole period, not just this one fund line
        self.assertEqual(popover["new_budget"], "300.00")
        self.assertEqual(popover["total"], "360.00")

        # The figure is a promise about the plan: it must match what it creates
        budget_allocation_id.action_done()
        plan_line_cc1 = budget_allocation_id.plan_id.line_ids.filtered(
            lambda line: line.analytic_account_id == self.costcenter1
        )
        self.assertEqual(plan_line_cc1.allocated_amount, 360.0)

        # A cancelled allocation contributes nothing
        budget_allocation_id.action_cancel()
        popover = loads(line_cc1.json_budget_popover)
        self.assertEqual(popover["new_budget"], "0.00")
        self.assertEqual(popover["total"], "60.00")

    @freeze_time("2001-02-01")
    def test_06_company_policy_targets_allocated_amount(self):
        previous_period = self.env["budget.period"].create(
            {
                "name": "Budget for FY Prev (Allocated Policy)",
                "template_id": self.template.id,
                "bm_date_from": "%s-01-01" % (self.year - 1),
                "bm_date_to": "%s-12-31" % (self.year - 1),
                "plan_date_range_type_id": self.date_range_type.id,
                "control_level": "analytic_kpi",
            }
        )
        forward = self.env["budget.balance.forward"].create(
            {
                "name": "Forward for Allocated Policy",
                "from_budget_period_id": previous_period.id,
                "to_budget_period_id": self.budget_period.id,
            }
        )
        forward_only = self.AnalyticAccount.create(
            {
                "name": "Forward Only",
                "budget_period_id": self.budget_period.id,
            }
        )
        for analytic, amount in ((self.costcenter1, 400.0), (forward_only, 50.0)):
            self.env["budget.balance.forward.line"].create(
                {
                    "forward_id": forward.id,
                    "analytic_account_id": analytic.id,
                    "amount_balance": amount,
                    "amount_balance_forward": amount,
                }
            )
        forward.action_budget_balance_forward()

        self.env.company.budget_allocation_amount_basis = "new_budget"
        allocation = self._create_budget_allocation(100.0)
        self.assertEqual(allocation.amount_basis, "new_budget")
        allocation.action_done()
        plan = allocation.plan_id
        line_cc1 = plan.line_ids.filtered(
            lambda line: line.analytic_account_id == self.costcenter1
        )
        self.assertEqual(line_cc1.amount, 300.0)
        self.assertEqual(line_cc1.allocated_amount, 700.0)
        self.assertEqual(plan.total_amount, 850.0)

        settings = self.env["res.config.settings"].create(
            {"company_id": self.env.company.id}
        )
        settings.budget_allocation_amount_basis = "allocated"
        self.assertEqual(self.env.company.budget_allocation_amount_basis, "allocated")
        allocation.action_draft()
        allocation_line = allocation.line_ids.filtered(
            lambda line: line.analytic_account_id == self.costcenter1
        )[:1]
        popover = loads(allocation_line.json_budget_popover)
        self.assertEqual(popover["new_budget"].replace("\ufeff", ""), "-100.00")
        self.assertEqual(popover["total"], "300.00")

        allocation.action_done()
        self.assertEqual(allocation.amount_basis, "allocated")
        line_forward_only = plan.line_ids.filtered(
            lambda line: line.analytic_account_id == forward_only
        )
        self.assertEqual(plan.company_id, allocation.company_id)
        self.assertEqual(line_cc1.amount, -100.0)
        self.assertEqual(line_cc1.allocated_amount, 300.0)
        self.assertEqual(line_forward_only.amount, 0.0)
        self.assertEqual(line_forward_only.allocated_amount, 50.0)
        self.assertEqual(plan.init_amount, 400.0)
        self.assertEqual(plan.total_amount, 450.0)
        plan.action_confirm()
        self.assertEqual(plan.state, "confirm")
        # A later settings change does not rewrite an already completed plan.
        self.env.company.budget_allocation_amount_basis = "new_budget"
        self.assertEqual(allocation.amount_basis, "allocated")
        self.assertEqual(line_cc1.amount, -100.0)
