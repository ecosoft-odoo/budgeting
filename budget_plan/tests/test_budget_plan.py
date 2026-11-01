# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from freezegun import freeze_time

from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from odoo.addons.budget_control.tests.common import BudgetControlCommon


@tagged("post_install", "-at_install")
class TestBudgetPlan(BudgetControlCommon):
    @classmethod
    @freeze_time("2001-02-01")
    def setUpClass(cls):
        super().setUpClass()
        cls.BudgetPlan = cls.env["budget.plan"]
        cls.PlanAnalyticSelect = cls.env["budget.plan.analytic.select"]

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
            name=f"Test - Plan {cls.budget_period.name}",
            budget_period=cls.budget_period,
            lines=lines,
        )
        cls.budget_plan.action_confirm()
        cls.budget_plan.action_create_update_budget_control()
        cls.budget_plan.action_done()
        cls.budget_plan.invalidate_recordset()
        cls.budget_control, cls.budget_control2 = cls.budget_plan.budget_control_ids
        for control in cls.budget_plan.budget_control_ids:
            control.use_all_kpis = True
            control.prepare_budget_control_matrix()
            # KPI1 = 100x4=400, KPI2=800, KPI3=1,200
            for kpi, amount in ((cls.kpi1, 100), (cls.kpi2, 200), (cls.kpi3, 300)):
                control.line_ids.filtered(lambda x, kpi=kpi: x.kpi_id == kpi).write(
                    {"amount": amount}
                )

    def create_budget_plan(self, name, budget_period, lines=False):
        return self.BudgetPlan.create(
            {
                "name": name,
                "budget_period_id": budget_period.id,
                "line_ids": lines,
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

    def _create_next_period(self):
        self._create_date_range_quarter(self.year + 1)
        return self.env["budget.period"].create(
            {
                "name": f"Budget for FY{self.year + 1}",
                "template_id": self.template.id,
                "bm_date_from": f"{self.year + 1}-01-01",
                "bm_date_to": f"{self.year + 1}-12-31",
                "plan_date_range_type_id": self.date_range_type.id,
                "control_level": "analytic_kpi",
            }
        )

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
        # Lines of several plans are checked plan by plan
        other_plan = self.create_budget_plan(
            name="Other plan",
            budget_period=self.budget_period,
            lines=[
                Command.create(
                    {"analytic_account_id": self.costcenter1.id, "amount": 10.0}
                )
            ],
        )
        copies = (self.budget_plan | other_plan).copy()
        self.assertEqual(len(copies.line_ids), 3)

    @freeze_time("2001-02-01")
    def test_03_budget_plan_check_control(self):
        self.assertEqual(len(self.budget_plan.budget_control_ids), 2)
        self.assertTrue(
            all(
                control.budget_plan_id == self.budget_plan
                for control in self.budget_plan.budget_control_ids
            )
        )
        action = self.budget_plan.button_open_budget_control()
        self.assertEqual(
            action["domain"][0][2], self.budget_plan.budget_control_ids.ids
        )

    @freeze_time("2001-02-01")
    def test_04_budget_plan_adopts_unowned_control(self):
        """A plan owns an existing manual control before updating its amount."""
        analytic = self.Analytic.create(
            {"name": "Adopted control", "plan_id": self.aa_plan1.id}
        )
        # Plan ranges of 2002 are needed for the sheets of continuing analytics
        period = self._create_next_period()
        control = self.BudgetControl.create(
            {
                "name": "Manual control",
                "analytic_account_id": analytic.id,
                "budget_period_id": period.id,
                "plan_date_range_type_id": self.date_range_type.id,
                "currency_id": self.env.company.currency_id.id,
                "allocated_amount": 125.0,
            }
        )
        plan = self.create_budget_plan(
            name="Adopting plan",
            budget_period=period,
            lines=[
                Command.create({"analytic_account_id": analytic.id, "amount": 500.0})
            ],
        )
        plan.action_confirm()
        # A plan does not take over a sheet already under review or control
        control.state = "submit"
        with self.assertRaisesRegex(UserError, "to draft before Budget Plan"):
            plan.action_create_update_budget_control()
        self.assertFalse(control.budget_plan_id)
        self.assertEqual(control.state, "submit")
        control.action_draft()
        plan.action_create_update_budget_control()

        self.assertEqual(control.budget_plan_id, plan)
        self.assertEqual(control.action_view_budget_plan()["res_id"], plan.id)
        # The other sheets are of the analytics continuing from 2001
        self.assertEqual(
            plan.budget_control_ids.filtered(
                lambda sheet: sheet.analytic_account_id == analytic
            ),
            control,
        )
        self.assertAlmostEqual(control.allocated_amount, 500.0)

    @freeze_time("2001-02-01")
    def test_05_budget_plan_cannot_take_another_plans_control(self):
        """A live control has exactly one managing Budget Plan."""
        other_plan = self.create_budget_plan(
            name="Conflicting plan",
            budget_period=self.budget_period,
            lines=[
                Command.create(
                    {"analytic_account_id": self.costcenter1.id, "amount": 100.0}
                )
            ],
        )
        other_plan.action_confirm()

        with self.assertRaisesRegex(
            UserError, "already managed by another Budget Plan"
        ):
            other_plan.action_create_update_budget_control()

        self.assertEqual(self.budget_control.budget_plan_id, self.budget_plan)

    def test_06_budget_plan_uses_only_fiscal_analytics(self):
        companies = self.env.company | self.company_b
        analytic_model = self.Analytic.with_context(allowed_company_ids=companies.ids)
        fiscal_analytic = analytic_model.create(
            {
                "name": "Fiscal Plan Analytic",
                "plan_id": self.aa_plan1.id,
                "company_id": self.env.company.id,
                "budget_period_id": self.budget_period.id,
            }
        )
        other_company_analytic = analytic_model.create(
            {
                "name": "Other Company Fiscal Analytic",
                "plan_id": self.aa_plan1.id,
                "company_id": self.company_b.id,
                "budget_period_id": self.budget_period.id,
            }
        )
        lifetime_analytic = analytic_model.create(
            {
                "name": "Lifetime Plan Analytic",
                "plan_id": self.aa_plan1.id,
                "company_id": self.env.company.id,
            }
        )
        lifetime_analytic._create_lifetime_budget_period(
            self._get_lifetime_period_vals("Lifetime Plan Analytic")
        )
        plan = self.BudgetPlan.with_context(allowed_company_ids=companies.ids).create(
            {
                "name": "Fiscal-only Budget Plan",
                "budget_period_id": self.budget_period.id,
                "company_ids": [Command.set(self.env.company.ids)],
            }
        )

        plan.action_update_plan()

        plan_analytics = plan.line_ids.mapped("analytic_account_id")
        self.assertIn(fiscal_analytic, plan_analytics)
        self.assertNotIn(lifetime_analytic, plan_analytics)
        self.assertNotIn(other_company_analytic, plan_analytics)

        plan.action_confirm()
        plan.action_create_update_budget_control()
        self.assertEqual(plan.budget_control_ids.analytic_account_id, fiscal_analytic)
        self.assertEqual(plan.budget_control_ids.budget_scope, "fiscal")

        with (
            self.assertRaisesRegex(ValidationError, "only Fiscal analytics"),
            self.env.cr.savepoint(),
        ):
            self.env["budget.plan.line"].create(
                {
                    "plan_id": plan.id,
                    "analytic_account_id": lifetime_analytic.id,
                }
            )

    @freeze_time("2001-02-01")
    def test_07_budget_transfer_released(self):
        """Plan-line Allocated remains the original funding while Released
        follows the completed transfers."""
        transfer = self._create_budget_transfer(
            budget_from=self.budget_control, budget_to=self.budget_control2, amount=40
        )
        transfer.action_submit()
        transfer.action_transfer()
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

        transfer.action_reverse()
        (self.budget_control | self.budget_control2)._compute_transferred_amount()
        self.budget_plan.check_plan_consumed()
        self.assertAlmostEqual(plan_line_from.released_amount, 2400.0)
        self.assertAlmostEqual(plan_line_to.released_amount, 2400.0)

    @freeze_time("2001-02-01")
    def test_08_balance_forward_on_plan(self):
        """The forward balance of a period is added to its plan allocation."""
        next_period = self._create_next_period()
        forward = self.env["budget.balance.forward"].create(
            {
                "name": "Test: Budget Balance Forward",
                "from_budget_period_id": self.budget_period.id,
                "to_budget_period_id": next_period.id,
            }
        )
        forward_line = self.env["budget.balance.forward.line"].create(
            {
                "forward_id": forward.id,
                "analytic_account_id": self.costcenter1.id,
                "amount_balance": 30.0,
                "amount_balance_forward": 20.0,
                "accumulate_analytic_account_id": self.costcenter1.id,
            }
        )
        next_plan = self.create_budget_plan(
            name="Budget Plan FY Next",
            budget_period=next_period,
            lines=[
                Command.create(
                    {"analytic_account_id": self.costcenter1.id, "amount": 20.0}
                )
            ],
        )
        self.assertEqual(next_plan.line_ids.amount_forward_in, 0.0)
        self.assertEqual(next_plan.line_ids.allocated_amount, 20.0)

        forward.action_budget_balance_forward()
        self.assertEqual(next_plan.line_ids.amount_forward_in, 30.0)
        self.assertEqual(next_plan.line_ids.allocated_amount, 50.0)
        self.assertEqual(next_plan.total_amount, 50.0)
        # The lines of a done forward keep what it carried to the plan
        with self.assertRaisesRegex(UserError, "cannot change"):
            forward_line.amount_balance = 40.0

        # A plan with only the forward balance
        carry_only_plan = self.create_budget_plan(
            name="Carry Only Budget Plan FY Next",
            budget_period=next_period,
            lines=[
                Command.create(
                    {"analytic_account_id": self.costcenter1.id, "amount": 0.0}
                )
            ],
        )
        self.assertEqual(carry_only_plan.line_ids.allocated_amount, 30.0)

        # A confirmed target plan has taken the forward balance
        next_plan.action_confirm()
        with self.assertRaisesRegex(UserError, "Reverse Forward"):
            forward.action_cancel()
        self.assertEqual(forward.state, "done")

        next_plan.action_create_update_budget_control()
        target_control = next_plan.budget_control_ids.filtered(
            lambda control: control.analytic_account_id == self.costcenter1
        )
        self.assertEqual(target_control.budget_period_id, next_period)
        self.assertEqual(target_control.allocated_amount, 50.0)
        self.assertEqual(target_control.amount_forward_in, 30.0)

        with self.assertRaisesRegex(ValidationError, "cannot be negative"):
            self.create_budget_plan(
                name="Invalid Negative Budget",
                budget_period=next_period,
                lines=[
                    Command.create(
                        {"analytic_account_id": self.costcenterX.id, "amount": -1.0}
                    )
                ],
            )

    @freeze_time("2001-02-01")
    def test_09_plan_period_setup(self):
        """A plan uses a fiscal period set up for budget control."""
        analytic = self.Analytic.create(
            {"name": "Lifetime Plan Guard", "plan_id": self.aa_plan1.id}
        )
        lifetime_period = analytic._create_lifetime_budget_period(
            self._get_lifetime_period_vals("Lifetime Plan Guard")
        )
        with self.assertRaisesRegex(ValidationError, "Budget Plans use Fiscal Periods"):
            self.create_budget_plan(
                name="Invalid Lifetime Budget Plan", budget_period=lifetime_period
            )
        period = self.env["budget.period"].create(
            {
                "name": "Budget for FY2003",
                "bm_date_from": "2003-01-01",
                "bm_date_to": "2003-12-31",
                "template_id": False,
            }
        )
        plan = self.create_budget_plan(name="Plan FY2003", budget_period=period)
        with self.assertRaisesRegex(UserError, "Plan Date Range of Budget Period"):
            plan.action_create_update_budget_control()

    def test_10_budget_control_views(self):
        """Sheets are created from their plan, which manages their allocation."""
        views = self.BudgetControl.get_views([(False, "list"), (False, "form")])
        for view_type in ("list", "form"):
            self.assertIn('create="0"', views["views"][view_type]["arch"])
        self.assertIn("budget_plan_id", views["views"]["form"]["arch"])

    @freeze_time("2001-02-01")
    def test_11_budget_plan_details(self):
        """A plan line is allocated by fund in its details, with one budget
        control sheet for the analytic, and the budget period controls the
        allocations."""
        fund_plan = self.AnalyticPlan.create({"name": "Fund", "control_budget": False})
        fund_a = self.Analytic.create({"name": "Fund A", "plan_id": fund_plan.id})
        fund_b = self.Analytic.create({"name": "Fund B", "plan_id": fund_plan.id})
        fund_c = self.Analytic.create({"name": "Fund C", "plan_id": fund_plan.id})
        report_plan = self.AnalyticPlan.create(
            {"name": "Report", "control_budget": False}
        )
        report_a = self.Analytic.create({"name": "Report A", "plan_id": report_plan.id})
        fname = fund_plan._budget_column_name()
        report_fname = report_plan._budget_column_name()

        # A plan of the next period: one sheet for the analytic
        plan = self.create_budget_plan(
            name="Plan by fund",
            budget_period=self._create_next_period(),
            lines=[
                Command.create(
                    {
                        "analytic_account_id": self.costcenter1.id,
                        "detail_ids": [
                            Command.create({"amount": 100.0, fname: fund_a.id}),
                            Command.create({"amount": 50.0, fname: fund_b.id}),
                        ],
                    }
                ),
            ],
        )
        line = plan.line_ids
        self.assertEqual(line.amount, 150.0)
        self.assertEqual(line.action_open_details()["res_id"], line.id)
        with self.assertRaisesRegex(ValidationError, "Duplicate allocation"):
            line.detail_ids = [Command.create({fname: fund_a.id})]
        # Accounts stay in the column of their plan
        with self.assertRaisesRegex(
            ValidationError, "outside the column of their plan in the details"
        ):
            line.detail_ids[:1][fname] = report_a
        # A plan mandatory in budget plans is needed on each detail
        report_plan.applicability_ids = [
            Command.create({"business_domain": "budget", "applicability": "mandatory"})
        ]
        with self.assertRaisesRegex(
            ValidationError,
            "Mandatory plans missing in the details of CostCenter1:\n"
            "- Fund A: Report\n",
        ):
            line.detail_ids = [Command.create({report_fname: report_a.id})]
        report_plan.applicability_ids = [Command.clear()]
        # A shared analytic account follows the companies of its plan
        shared = self.Analytic.create(
            {"name": "Shared", "plan_id": self.aa_plan1.id, "company_id": False}
        )
        company_b = self.env["res.company"].create(
            {"name": "Budget Company B", "currency_id": plan.currency_id.id}
        )
        plan.line_ids = [
            Command.create(
                {
                    "analytic_account_id": shared.id,
                    "detail_ids": [Command.create({"amount": 10.0, fname: fund_a.id})],
                }
            )
        ]
        report_plan.applicability_ids = [
            Command.create(
                {
                    "business_domain": "budget",
                    "applicability": "mandatory",
                    "company_id": company_b.id,
                }
            )
        ]
        with self.assertRaisesRegex(
            ValidationError, "Mandatory plans missing in the details of Shared"
        ):
            plan.company_ids |= company_b
        report_plan.applicability_ids = [Command.clear()]
        plan.line_ids.filtered(lambda line: line.analytic_account_id == shared).unlink()
        # Details are checked once all are written, e.g. swapping their funds
        detail_1, detail_2 = line.detail_ids
        line.write(
            {
                "detail_ids": [
                    Command.update(detail_1.id, {fname: fund_b.id}),
                    Command.update(detail_2.id, {fname: fund_a.id}),
                ]
            }
        )
        plan.action_confirm()
        plan.action_create_update_budget_control()
        sheet = plan.budget_control_ids.filtered(
            lambda sheet: sheet.analytic_account_id == self.costcenter1
        )
        self.assertEqual(len(sheet), 1)
        self.assertEqual(sheet.allocated_amount, 150.0)

        # Allocate the budget of this period by fund
        cc1_line = self.budget_plan.line_ids.filtered(
            lambda line: line.analytic_account_id == self.costcenter1
        )
        cc1_line.detail_ids = [
            Command.create({"amount": 2000.0, fname: fund_a.id}),
            Command.create({"amount": 400.0, fname: fund_b.id}),
        ]
        self.assertEqual(cc1_line.amount, 2400.0)
        self.budget_period.write({"control_budget": True, "control_level": "analytic"})
        self.assertTrue(self.budget_period.control_allocation)
        sheets = self.budget_plan.budget_control_ids
        sheets.action_submit()
        sheets.action_done()
        key_a = f"{self.costcenter1.id},{fund_a.id}"
        key_b = f"{self.costcenter1.id},{fund_b.id}"

        def bill(distribution, amount):
            return self.Move.create(
                {
                    "move_type": "in_invoice",
                    "partner_id": self.vendor.id,
                    "invoice_date": "2001-02-01",
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "quantity": 1,
                                "account_id": self.account_kpi1.id,
                                "price_unit": amount,
                                "analytic_distribution": distribution,
                            }
                        )
                    ],
                }
            )

        bill({key_a: 60, key_b: 40}, 500).action_post()
        # The sheet shows its allocations, also to its budget users
        cc1_control = sheets.filtered(
            lambda control: control.analytic_account_id == self.costcenter1
        )
        cc1_control.assignee_ids = self.budget_user
        allocations = cc1_control.with_user(self.budget_user).allocation_ids
        self.assertEqual(allocations, cc1_line.detail_ids)
        self.assertEqual(
            [
                (detail.amount, detail.amount_consumed, detail.amount_available)
                for detail in allocations
            ],
            [(2000.0, 300.0, 1700.0), (400.0, 200.0, 200.0)],
        )
        arch = (
            self.env["budget.control"]
            .with_user(self.budget_user)
            .get_views([(False, "form")])["views"]["form"]["arch"]
        )
        self.assertIn(f'name="{fname}"', arch)
        bill2 = bill({key_b: 100}, 300)
        with self.assertRaisesRegex(
            UserError, "CostCenter1 / Fund B allocation, will result in"
        ):
            bill2.action_post()
        with self.assertRaisesRegex(UserError, "CostCenter1 / Fund C is not allocated"):
            bill({f"{self.costcenter1.id},{fund_c.id}": 100}, 10).action_post()
        with self.assertRaisesRegex(UserError, "CostCenter1 is not allocated"):
            bill({self.costcenter1.id: 100}, 10).action_post()
        # A detail may split a fund by another plan: documents without an
        # account of it keep matching the fund alone
        cc1_line.detail_ids = [
            Command.create(
                {"amount": 100.0, fname: fund_a.id, report_fname: report_a.id}
            )
        ]
        key_a_report = f"{self.costcenter1.id},{fund_a.id},{report_a.id}"
        bill({key_a_report: 100}, 100).action_post()
        with self.assertRaisesRegex(
            UserError, "CostCenter1 / Fund A / Report A allocation, will result in"
        ):
            bill({key_a_report: 100}, 1).action_post()
        with self.assertRaisesRegex(
            UserError, "CostCenter1 / Fund B / Report A is not allocated"
        ):
            bill(
                {f"{self.costcenter1.id},{fund_b.id},{report_a.id}": 100}, 1
            ).action_post()
        bill({key_a: 100}, 1).action_post()
        # The allocations stay with their consumed analytic account and period
        with self.assertRaisesRegex(
            ValidationError, "Cannot move the details of CostCenter1"
        ):
            cc1_line.analytic_account_id = self.costcenterX
        with self.assertRaisesRegex(
            ValidationError, "Cannot move the details of CostCenter1"
        ):
            self.budget_plan.budget_period_id = plan.budget_period_id
        # The details cover the commitments and actuals of the period
        detail_a, detail_b = cc1_line.detail_ids[:2]
        with self.assertRaisesRegex(ValidationError, "Fund B cannot be allocated less"):
            detail_b.amount = 100.0
        with self.assertRaisesRegex(
            ValidationError, "Keep a detail for CostCenter1 / Fund A: .* already"
        ):
            detail_a.unlink()
        with self.assertRaisesRegex(
            ValidationError, "Cannot remove all the details of CostCenter1"
        ):
            cc1_line.detail_ids.unlink()
        with self.assertRaisesRegex(
            ValidationError, "Cannot remove all the details of CostCenter1"
        ):
            cc1_line.detail_ids = [Command.clear()]
        with self.assertRaisesRegex(
            ValidationError, "Cannot remove all the details of CostCenter1"
        ):
            cc1_line.unlink()
        # A dimension added now would not count them
        with self.assertRaisesRegex(
            ValidationError, "Keep a detail for CostCenter1 / Fund B: .* already"
        ):
            detail_b[report_fname] = report_a
        with self.assertRaisesRegex(UserError, "cannot move to another plan line"):
            detail_a.plan_line_id = line
        # The allocations are checked while their plan is revised
        self.budget_plan.action_draft()
        with self.assertRaisesRegex(UserError, "Fund B allocation, will result"):
            bill2.action_post()
        self.budget_plan.action_done()
        # Without Control Allocation, allocations are for information only
        self.budget_period.control_allocation = False
        bill2.action_post()
        # Analytics without details are not checked
        bill({self.costcenterX.id: 100}, 10).action_post()

    @freeze_time("2001-02-01")
    def test_12_plan_yearly_and_continuing_analytics(self):
        """A plan takes the yearly analytics of its period, and the analytics
        without Budget Period open in it, dated or budgeted the period
        before."""
        next_period = self._create_next_period()
        yearly, extended, unbudgeted, dated = self.Analytic.create(
            [
                {
                    "name": "Yearly",
                    "plan_id": self.aa_plan1.id,
                    "budget_period_id": next_period.id,
                },
                {
                    "name": "Extended",
                    "plan_id": self.aa_plan1.id,
                    "budget_period_id": self.budget_period.id,
                },
                {"name": "Unbudgeted", "plan_id": self.aa_plan1.id},
                {
                    "name": "Dated",
                    "plan_id": self.aa_plan1.id,
                    "bm_date_from": next_period.bm_date_from,
                    "bm_date_to": next_period.bm_date_to,
                },
            ]
        )
        extended.bm_date_to = next_period.bm_date_to
        plan = self.create_budget_plan(
            name="Budget Plan FY Next", budget_period=next_period
        )
        plan.action_update_plan()
        analytics = plan.line_ids.analytic_account_id
        # Open-ended analytics budgeted the period before continue
        self.assertIn(self.costcenter1, analytics)
        self.assertIn(yearly, analytics)
        self.assertIn(dated, analytics)
        self.assertNotIn(extended, analytics)
        self.assertNotIn(unbudgeted, analytics)

    @freeze_time("2001-02-01")
    def test_13_details_allocate_forward_balance(self):
        """The details of a line allocate its new budget and forward balance:
        a forward completed after them is left unallocated until they do."""
        fund_plan = self.AnalyticPlan.create({"name": "Fund", "control_budget": False})
        fund_a, fund_b = self.Analytic.create(
            [{"name": f"Fund {name}", "plan_id": fund_plan.id} for name in "AB"]
        )
        fname = fund_plan._budget_column_name()
        next_period = self._create_next_period()
        plan = self.create_budget_plan(
            name="Plan with forward balance",
            budget_period=next_period,
            lines=[
                Command.create(
                    {
                        "analytic_account_id": self.costcenter1.id,
                        "detail_ids": [
                            Command.create({"amount": 20.0, fname: fund_a.id})
                        ],
                    }
                )
            ],
        )
        line = plan.line_ids
        self.assertEqual(line.amount, 20.0)
        forward = self.env["budget.balance.forward"].create(
            {
                "name": "Forward to the allocated plan",
                "from_budget_period_id": self.budget_period.id,
                "to_budget_period_id": next_period.id,
            }
        )
        self.env["budget.balance.forward.line"].create(
            {
                "forward_id": forward.id,
                "analytic_account_id": self.costcenter1.id,
                "amount_balance": 30.0,
                "amount_balance_forward": 30.0,
            }
        )
        forward.action_budget_balance_forward()
        self.assertEqual(line.amount_forward_in, 30.0)
        self.assertEqual(line.amount, 20.0)
        self.assertEqual(line.allocated_amount, 50.0)
        self.assertEqual(line.amount_unallocated, 30.0)
        with self.assertRaisesRegex(UserError, "unallocated"):
            plan.action_confirm()
        line.detail_ids = [Command.create({"amount": 30.0, fname: fund_b.id})]
        self.assertEqual(line.amount, 20.0)
        self.assertFalse(line.amount_unallocated)
        plan.action_confirm()
        self.assertEqual(plan.state, "confirm")
