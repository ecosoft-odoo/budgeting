# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

from odoo import Command

from odoo.addons.budget_control.tests.common import BudgetControlCommon


class BudgetPlanDetailCommon(BudgetControlCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.check_plan_detail_installed = cls.env["ir.module.module"].search_count(
            [("name", "=", "budget_plan_detail"), ("state", "=", "installed")], limit=1
        )
        if cls.check_plan_detail_installed:
            cls.PlanLineDetail = cls.env["budget.plan.line.detail"]
            cls.BudgetFundGroup = cls.env["budget.source.fund.group"]
            cls.AnalyticDimension = cls.env["account.analytic.dimension"]
            cls.AnalyticTag = cls.env["account.analytic.tag"]
            cls.BudgetFund = cls.env["budget.source.fund"]

            # Create fund group
            cls.fund_group1 = cls.BudgetFundGroup.create({"name": "Test FG 1"})
            cls.fund_group2 = cls.BudgetFundGroup.create({"name": "Test FG 2"})
            # Create fund
            cls.fund1_g1 = cls.BudgetFund.create(
                {"name": "Test Fund 1", "fund_group_id": cls.fund_group1.id}
            )
            cls.fund2_g1 = cls.BudgetFund.create(
                {"name": "Test Fund 2", "fund_group_id": cls.fund_group1.id}
            )
            cls.fund3_g2 = cls.BudgetFund.create(
                {"name": "Test Fund 3", "fund_group_id": cls.fund_group2.id}
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

    def create_budget_plan(
        self, name, budget_period, lines=False, skip_line_detail=False
    ):
        budget_plan = self.BudgetPlan.create(
            {
                "name": name,
                "budget_period_id": budget_period.id,
                "line_ids": lines,
            }
        )
        if self.check_plan_detail_installed and not skip_line_detail:
            self._create_budget_plan_line_detail(self, budget_plan)
        return budget_plan

    def _create_simple_bill(
        self,
        analytic_distribution,
        account,
        amount,
        analytic_tag=False,
        default_tag=True,
        fund=False,
        default_fund=True,
    ):
        """Overwrite"""
        if self.check_plan_detail_installed:
            if not analytic_tag and default_tag:
                analytic_tag = self.analytic_tag1
            if not fund and default_fund:
                fund = self.fund1_g1

            invoice_list = {
                "move_type": "in_invoice",
                "partner_id": self.vendor.id,
                "invoice_date": datetime.today(),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "quantity": 1,
                            "account_id": account.id,
                            "price_unit": amount,
                            "analytic_distribution": analytic_distribution,
                            "analytic_tag_ids": analytic_tag
                            and [(4, analytic_tag.id)]
                            or False,
                            "fund_id": fund and fund.id or False,
                        },
                    )
                ],
            }
        # Use standard from budget control
        else:
            invoice_list = {
                "move_type": "in_invoice",
                "partner_id": self.vendor.id,
                "invoice_date": datetime.today(),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "quantity": 1,
                            "account_id": account.id,
                            "price_unit": amount,
                            "analytic_distribution": analytic_distribution,
                        },
                    )
                ],
            }
        invoice = self.Move.create(invoice_list)
        return invoice

    def _create_budget_transfer(
        self,
        budget_from,
        budget_to,
        amount,
        fund_from=False,
        fund_to=False,
        analytic_tag_from=False,
        analytic_tag_to=False,
    ):
        line_vals = {
            "budget_control_from_id": budget_from.id,
            "budget_control_to_id": budget_to.id,
            "amount": amount,
        }
        if self.check_plan_detail_installed:
            # Default is Fund1, Tag1
            if analytic_tag_from != [] and not analytic_tag_from:
                analytic_tag_from = budget_from.analytic_tag_ids[0]
            if analytic_tag_to != [] and not analytic_tag_to:
                analytic_tag_to = budget_to.analytic_tag_ids[0]
            fund_from = fund_from or budget_from.fund_ids[0]
            fund_to = fund_to or budget_to.fund_ids[0]
            line_vals.update(
                {
                    "fund_from_id": fund_from.id,
                    "analytic_tag_from_ids": analytic_tag_from
                    and [Command.set(analytic_tag_from.ids)]
                    or [],
                    "fund_to_id": fund_to.id,
                    "analytic_tag_to_ids": analytic_tag_to
                    and [Command.set(analytic_tag_to.ids)]
                    or [],
                }
            )
        budget_transfer = self.BudgetTransfer.create(
            {"transfer_item_ids": [Command.create(line_vals)]}
        )
        return budget_transfer

    def _create_budget_plan_line_detail(
        self, budget_plan, lines_detail=False, amount=600.0, auto_confirm=True
    ):
        if not lines_detail:
            # Create same analytic, difference fund, difference analytic tags
            # line 1: Costcenter1, Fund1, Tag1, 600.0
            # line 2: Costcenter1, Fund1, Tag2, 600.0
            # line 3: Costcenter1, Fund2, Tag1, 600.0
            # line 4: Costcenter1, Fund2,     , 600.0
            # line 5: CostcenterX, Fund1, Tag1, 600.0
            # line 6: CostcenterX, Fund2, Tag1, 600.0
            # line 7: CostcenterX, Fund2, Tag2, 600.0
            # line 8: CostcenterX, Fund1,     , 600.0
            lines_detail = [
                # Line 1 - 4
                {
                    "plan_id": budget_plan.id,
                    "analytic_account_id": self.costcenter1.id,
                    "fund_id": self.fund1_g1.id,
                    "analytic_tag_ids": [(4, self.analytic_tag1.id)],
                    "allocated_amount": amount,
                },
                {
                    "plan_id": budget_plan.id,
                    "analytic_account_id": self.costcenter1.id,
                    "fund_id": self.fund1_g1.id,
                    "analytic_tag_ids": [(4, self.analytic_tag2.id)],
                    "allocated_amount": amount,
                },
                {
                    "plan_id": budget_plan.id,
                    "analytic_account_id": self.costcenter1.id,
                    "fund_id": self.fund2_g1.id,
                    "analytic_tag_ids": [(4, self.analytic_tag1.id)],
                    "allocated_amount": amount,
                },
                {
                    "plan_id": budget_plan.id,
                    "analytic_account_id": self.costcenter1.id,
                    "fund_id": self.fund2_g1.id,
                    "allocated_amount": amount,
                },
                # Line 5 - 8
                {
                    "plan_id": budget_plan.id,
                    "analytic_account_id": self.costcenterX.id,
                    "fund_id": self.fund1_g1.id,
                    "analytic_tag_ids": [(4, self.analytic_tag1.id)],
                    "allocated_amount": amount,
                },
                {
                    "plan_id": budget_plan.id,
                    "analytic_account_id": self.costcenterX.id,
                    "fund_id": self.fund2_g1.id,
                    "analytic_tag_ids": [(4, self.analytic_tag1.id)],
                    "allocated_amount": amount,
                },
                {
                    "plan_id": budget_plan.id,
                    "analytic_account_id": self.costcenterX.id,
                    "fund_id": self.fund2_g1.id,
                    "analytic_tag_ids": [(4, self.analytic_tag2.id)],
                    "allocated_amount": amount,
                },
                {
                    "plan_id": budget_plan.id,
                    "analytic_account_id": self.costcenterX.id,
                    "fund_id": self.fund1_g1.id,
                    "allocated_amount": amount,
                },
            ]
        # Create budget plan line detail
        self.PlanLineDetail.create(lines_detail)
        # Update Plan line and Detail
        if auto_confirm:
            budget_plan.action_confirm_plan_detail()
        return budget_plan
