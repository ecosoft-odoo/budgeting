# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from freezegun import freeze_time

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import new_test_user, tagged

from odoo.addons.budget_control.tests.common import get_budget_common_class


@tagged("post_install", "-at_install")
class TestBudgetControlSaleStock(get_budget_common_class()):
    @classmethod
    @freeze_time("2001-02-01")
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.Partner.create({"name": "Test Customer"})
        # Set cost price on products (purchase_price defaults from standard_price)
        cls.product1.write({"standard_price": 50.0})
        cls.product2.write({"standard_price": 80.0})
        cls.project_service = cls.Product.create(
            {
                "name": "Project Service",
                "type": "service",
                "service_tracking": "project_only",
                "standard_price": 120.0,
                "list_price": 200.0,
            }
        )
        # Project linked to costcenter1 analytic account
        cls.project = cls.env["project.project"].create(
            {
                "name": "Test Sales Project",
                "account_id": cls.costcenter1.id,
            }
        )
        # Analytic plan for sale budget (used when SO has no project)
        cls.sale_plan = cls.AnalyticPlan.create({"name": "Sale Budget Plan"})
        cls.budget_user = new_test_user(
            cls.env,
            login="sale-budget-user",
            groups=(
                "budget_control.group_budget_control_user,"
                "project.group_project_user,"
                "sales_team.group_sale_salesman_all_leads"
            ),
        )

    def _create_sale_order(self, project=None, lines=None, pricelist=None):
        """Create SO with optional project and order lines."""
        vals = {"partner_id": self.customer.id}
        if project:
            vals["project_id"] = project.id
        if pricelist:
            vals["pricelist_id"] = pricelist.id
        order = self.env["sale.order"].create(vals)
        if lines:
            for lv in lines:
                lv["order_id"] = order.id
                self.env["sale.order.line"].create(lv)
        return order

    @freeze_time("2001-02-01")
    def test_01_so_confirm_creates_budget_control(self):
        """
        Full flow: confirm SO with project -> BC auto-created.
        Computed fields (sale_price, gross_profit, gross_profit_percent) correct.
        Action buttons return correct actions.
        Re-confirm (reset to draft) -> same BC, no double allocated_amount.
        """
        sale = self._create_sale_order(
            project=self.project,
            lines=[
                {
                    "product_id": self.product1.id,
                    "product_uom_qty": 2,
                    "price_unit": 150.0,
                    "purchase_price": 50.0,
                },
                {
                    "product_id": self.product2.id,
                    "product_uom_qty": 1,
                    "price_unit": 200.0,
                    "purchase_price": 80.0,
                },
            ],
        )
        self.assertFalse(sale.budget_control_id)

        sale.action_confirm()
        self.assertEqual(sale.state, "sale")
        self.assertTrue(sale.budget_control_id)

        bc = sale.budget_control_id
        # allocated_amount = (50*2) + (80*1) = 180
        self.assertAlmostEqual(bc.allocated_amount, 180.0)
        self.assertFalse(bc.budget_plan_id)
        self.assertIn(sale, bc.sale_order_ids)
        self.assertEqual(bc.sale_order_count, 1)

        # sale_price = sum of SO amount_untaxed
        self.assertAlmostEqual(bc.sale_price, sale.amount_untaxed)
        # gross_profit = sale_price - current allocated budget
        expected_profit = sale.amount_untaxed - 180.0
        self.assertAlmostEqual(bc.gross_profit, expected_profit)
        if sale.amount_untaxed:
            expected_pct = expected_profit / sale.amount_untaxed * 100
            self.assertAlmostEqual(bc.gross_profit_percent, expected_pct, places=2)

        # action_open_budget_control from SO -> opens BC form
        action = sale.action_open_budget_control()
        self.assertEqual(action["res_model"], "budget.control")
        self.assertEqual(action["res_id"], bc.id)

        # action_open_sale_order from BC -> lists linked SOs
        action2 = bc.action_open_sale_order()
        self.assertEqual(action2["res_model"], "sale.order")
        self.assertIn(sale.id, action2["domain"][0][2])

        # Re-confirm: cancel -> draft -> confirm -> same BC, no doubling
        # Use _action_cancel to bypass the cancel wizard
        sale._action_cancel()
        sale.action_draft()
        sale.action_confirm()
        self.assertEqual(sale.budget_control_id, bc)
        # allocated_amount unchanged - same SO already in sale_order_ids
        self.assertAlmostEqual(bc.allocated_amount, 180.0)

    @freeze_time("2001-02-01")
    def test_02_second_so_same_analytic_accumulates(self):
        """
        Two SOs on same analytic+period -> second SO adds to existing BC.
        sale_order_count reflects both.
        """
        sale1 = self._create_sale_order(
            project=self.project,
            lines=[
                {
                    "product_id": self.product1.id,
                    "product_uom_qty": 2,
                    "price_unit": 100.0,
                    "purchase_price": 50.0,
                },
            ],
        )
        sale2 = self._create_sale_order(
            project=self.project,
            lines=[
                {
                    "product_id": self.product2.id,
                    "product_uom_qty": 3,
                    "price_unit": 100.0,
                    "purchase_price": 80.0,
                },
            ],
        )

        sale1.action_confirm()
        bc = sale1.budget_control_id
        # (50*2) = 100
        self.assertAlmostEqual(bc.allocated_amount, 100.0)
        # Keep a manual adjustment separate from the SO estimated cost.
        bc.allocated_amount = 125.0
        self.assertAlmostEqual(bc.gross_profit, 75.0)

        sale2.action_confirm()
        # sale2 must link to same existing BC (same analytic + period)
        self.assertEqual(sale2.budget_control_id, bc)
        # SO cost accumulates to 340; the manual adjustment remains 25.
        self.assertAlmostEqual(bc.allocated_amount, 365.0)
        self.assertAlmostEqual(bc.gross_profit, 135.0)
        self.assertEqual(bc.sale_order_count, 2)

    @freeze_time("2001-02-01")
    def test_03_error_and_skip_cases(self):
        """
        (1) SO without project -> confirm -> no BC created (skip silently)
        (2) SO with project but date outside all budget periods -> UserError
        """
        # (1) No project -> skip silently, no BC
        sale_no_project = self._create_sale_order(
            lines=[
                {
                    "product_id": self.product1.id,
                    "product_uom_qty": 1,
                    "price_unit": 100.0,
                    "purchase_price": 50.0,
                },
            ],
        )
        sale_no_project.action_confirm()
        self.assertFalse(sale_no_project.budget_control_id)

        # (2) date outside budget period ->
        # UserError from manual create (date_order is not overwritten in draft)
        sale_out = self._create_sale_order(
            project=self.project,
            lines=[
                {
                    "product_id": self.product1.id,
                    "product_uom_qty": 1,
                    "price_unit": 100.0,
                    "purchase_price": 50.0,
                },
            ],
        )
        sale_out.write({"date_order": "1999-06-15 00:00:00"})
        with self.assertRaisesRegex(UserError, "No budget period"):
            sale_out.action_create_budget_control()

    @freeze_time("2001-02-01")
    def test_04_manual_create_budget_control(self):
        """
        Manual action_create_budget_control on draft SO -> BC created and linked.
        """
        sale = self._create_sale_order(
            project=self.project,
            lines=[
                {
                    "product_id": self.product1.id,
                    "product_uom_qty": 1,
                    "price_unit": 100.0,
                    "purchase_price": 60.0,
                },
            ],
        )
        self.assertFalse(sale.budget_control_id)

        result = sale.action_create_budget_control()
        self.assertTrue(result)
        self.assertTrue(sale.budget_control_id)
        # allocated_amount = 60*1 = 60
        self.assertAlmostEqual(sale.budget_control_id.allocated_amount, 60.0)

    @freeze_time("2001-02-01")
    def test_05_manual_create_no_config_no_project(self):
        """
        SO without project, no config -> manual create -> UserError.
        """
        self.env.company.budget_sale_analytic_plan_id = False
        sale = self._create_sale_order(
            lines=[
                {
                    "product_id": self.product1.id,
                    "product_uom_qty": 1,
                    "price_unit": 100.0,
                    "purchase_price": 50.0,
                },
            ],
        )
        with self.assertRaisesRegex(UserError, "Sale Budget Analytic Plan"):
            sale.action_create_budget_control()

    @freeze_time("2001-02-01")
    def test_06_manual_create_with_config_no_project(self):
        """
        SO without project, with config -> manual create -> BC created
        with analytic account using configured plan_id.
        """
        self.env.company.budget_sale_analytic_plan_id = self.sale_plan
        sale = self._create_sale_order(
            lines=[
                {
                    "product_id": self.product1.id,
                    "product_uom_qty": 2,
                    "price_unit": 100.0,
                    "purchase_price": 50.0,
                },
            ],
        )
        self.assertFalse(sale.budget_control_id)

        result = sale.action_create_budget_control()
        self.assertTrue(result)
        self.assertTrue(sale.budget_control_id)
        # allocated_amount = 50*2 = 100
        self.assertAlmostEqual(sale.budget_control_id.allocated_amount, 100.0)
        # Analytic account should use configured plan
        analytic = sale.budget_control_id.analytic_account_id
        self.assertEqual(analytic.plan_id, self.sale_plan)
        # SO lines should have analytic distribution
        for line in sale.order_line:
            self.assertIn(str(analytic.id), line.analytic_distribution or {})

    @freeze_time("2001-02-01")
    def test_07_foreign_currency_amounts_use_company_currency(self):
        """SO revenue and cost are converted before creating the budget."""
        foreign_currency = self.env["res.currency"].create(
            {"name": "XSS", "symbol": "XSS", "rounding": 0.01}
        )
        self.env["res.currency.rate"].create(
            {
                "name": fields.Date.today(),
                "rate": 2.0,
                "currency_id": foreign_currency.id,
                "company_id": self.env.company.id,
            }
        )
        pricelist = self.env["product.pricelist"].create(
            {
                "name": "Foreign Sale Pricelist",
                "currency_id": foreign_currency.id,
            }
        )
        sale = self._create_sale_order(
            project=self.project,
            pricelist=pricelist,
            lines=[
                {
                    "product_id": self.product1.id,
                    "product_uom_qty": 2,
                    "price_unit": 150.0,
                    "purchase_price": 50.0,
                }
            ],
        )

        sale.action_confirm()

        bc = sale.budget_control_id
        # Rate 2 means 300 foreign = 150 company and 100 foreign = 50 company.
        self.assertEqual(bc.currency_id, self.env.company.currency_id)
        self.assertAlmostEqual(bc.sale_price, 150.0)
        self.assertAlmostEqual(bc.allocated_amount, 50.0)
        self.assertAlmostEqual(bc.gross_profit, 100.0)

    @freeze_time("2001-02-01")
    def test_08_budget_currency_rate_is_extendable(self):
        """Revenue and cost conversions use the SO-specific rate hook."""
        sale = self._create_sale_order(
            project=self.project,
            lines=[
                {
                    "product_id": self.product1.id,
                    "product_uom_qty": 2,
                    "price_unit": 150.0,
                    "purchase_price": 50.0,
                }
            ],
        )

        with patch.object(
            type(sale),
            "_get_budget_control_currency_rate",
            return_value=0.25,
        ):
            sale.action_confirm()
            bc = sale.budget_control_id
            self.assertEqual(bc.currency_id, self.env.company.currency_id)
            self.assertAlmostEqual(bc.sale_price, 75.0)
            self.assertAlmostEqual(bc.allocated_amount, 25.0)
            self.assertAlmostEqual(bc.gross_profit, 50.0)

    def test_09_multi_year_project_uses_one_control_per_period(self):
        """A Fiscal Project uses one control in each annual period."""
        self.project.write(
            {
                "date_start": "2001-01-01",
                "date": "2003-12-31",
            }
        )
        period_2002 = self.budget_period.copy(
            {
                "name": "Budget for FY2002",
                "bm_date_from": "2002-01-01",
                "bm_date_to": "2002-12-31",
            }
        )
        period_2003 = self.budget_period.copy(
            {
                "name": "Budget for FY2003",
                "bm_date_from": "2003-01-01",
                "bm_date_to": "2003-12-31",
            }
        )
        controls = self.env["budget.control"]
        for year, product in (
            (2001, self.product1),
            (2002, self.product2),
            (2003, self.product1),
        ):
            with freeze_time(f"{year}-02-01"):
                sale = self._create_sale_order(
                    project=self.project,
                    lines=[
                        {
                            "product_id": product.id,
                            "product_uom_qty": 1,
                            "price_unit": 150.0,
                            "purchase_price": product.standard_price,
                        }
                    ],
                )
                sale.action_confirm()
                controls |= sale.budget_control_id

        self.assertEqual(len(controls), 3)
        self.assertEqual(
            set(controls.budget_period_id.ids),
            {self.budget_period.id, period_2002.id, period_2003.id},
        )
        self.assertEqual(self.project.budget_control_count, 3)
        action = self.project.action_open_budget_controls()
        self.assertIn(
            ("analytic_account_id", "=", self.project.account_id.id),
            action["domain"],
        )

    @freeze_time("2001-02-01")
    def test_10_project_carry_forward_reaches_next_period_control(self):
        """A carried Project balance remains visible on the next annual control."""
        self.project.write(
            {
                "date_start": "2001-01-01",
                "date": "2003-12-31",
            }
        )
        sale = self._create_sale_order(
            project=self.project,
            lines=[
                {
                    "product_id": self.product1.id,
                    "product_uom_qty": 1,
                    "price_unit": 150.0,
                    "purchase_price": 50.0,
                }
            ],
        )
        sale.action_confirm()
        source_control = sale.budget_control_id
        self.env["budget.control.line"].create(
            {
                "budget_control_id": source_control.id,
                "analytic_account_id": self.project.account_id.id,
                "template_line_id": self.template_line1.id,
                "date_from": self.budget_period.bm_date_from,
                "date_to": self.budget_period.bm_date_to,
                "amount": 500.0,
            }
        )
        self.project.account_id.invalidate_recordset(
            [
                "amount_budget",
                "amount_forward_in",
                "amount_forward_out",
                "amount_consumed",
                "amount_balance",
            ]
        )
        source_control.invalidate_recordset(
            ["amount_budget", "amount_consumed", "amount_balance"]
        )
        self.assertAlmostEqual(source_control.amount_budget, 500.0)
        self.assertGreater(source_control.amount_balance, 0.0)
        source_analytic = self.project.account_id.with_context(
            budget_period_ids=self.budget_period.ids,
            no_fwd_commit=True,
        )
        self.assertGreater(source_analytic.amount_balance, 0.0)
        next_period = self.budget_period.copy(
            {
                "name": "Budget for FY2002",
                "bm_date_from": "2002-01-01",
                "bm_date_to": "2002-12-31",
            }
        )
        forward = self.env["budget.balance.forward"].create(
            {
                "name": "Carry Multi-year Project",
                "from_budget_period_id": self.budget_period.id,
                "to_budget_period_id": next_period.id,
            }
        )
        forward.action_review_budget_balance()
        project_line = forward.forward_line_ids.filtered(
            lambda line: line.analytic_account_id == self.project.account_id
        )
        self.assertEqual(len(project_line), 1)
        self.assertEqual(project_line.to_analytic_account_id, self.project.account_id)
        self.assertGreater(project_line.amount_balance, 0.0)
        carry_amount = project_line.amount_balance_forward
        self.assertAlmostEqual(carry_amount, project_line.amount_balance)
        forward.action_budget_balance_forward()
        self.assertEqual(forward.state, "done")
        self.assertAlmostEqual(project_line.amount_balance_forward, carry_amount)
        matched_line = self.env["budget.balance.forward.line"].search(
            [
                ("id", "=", project_line.id),
                ("forward_id.state", "=", "done"),
                ("to_analytic_account_id", "=", self.project.account_id.id),
            ]
        )
        self.assertEqual(matched_line, project_line)
        forward_amounts = self.env[
            "budget.balance.forward.line"
        ]._get_forward_balance_map(
            next_period.ids,
            self.project.account_id.ids,
        )
        self.assertAlmostEqual(
            forward_amounts[(next_period.id, self.project.account_id.id)],
            carry_amount,
        )

        plan_vals = {
            "name": "Project Budget FY2002",
            "budget_period_id": next_period.id,
            "line_ids": [
                Command.create(
                    {
                        "analytic_account_id": self.project.account_id.id,
                        "amount": 100.0,
                    }
                )
            ],
        }
        if "is_confirm_plan" in self.BudgetPlan._fields:
            plan_vals["is_confirm_plan"] = True
        target_plan = self.BudgetPlan.create(plan_vals)
        target_plan.line_ids.invalidate_recordset(
            ["amount_forward_in", "allocated_amount"]
        )
        self.assertAlmostEqual(target_plan.line_ids.amount_forward_in, carry_amount)
        self.assertAlmostEqual(
            target_plan.line_ids.allocated_amount, 100.0 + carry_amount
        )
        target_plan.action_create_update_budget_control()
        target_control = target_plan.budget_control_ids

        self.assertNotEqual(target_control, source_control)
        self.assertEqual(target_control.budget_period_id, next_period)
        self.assertAlmostEqual(target_control.amount_forward_in, carry_amount)
        self.assertEqual(self.project.budget_control_count, 2)

    @freeze_time("2001-02-01")
    def test_11_budget_analytic_preserves_other_plan_distribution(self):
        """Adding the Project analytic follows Odoo's multi-plan convention."""
        other_plan = self.AnalyticPlan.create({"name": "Other Dimension"})
        other_analytic = self.Analytic.create(
            {"name": "Other Analytic", "plan_id": other_plan.id}
        )
        sale = self._create_sale_order(
            project=self.project,
            lines=[
                {
                    "product_id": self.product1.id,
                    "product_uom_qty": 1,
                    "price_unit": 150.0,
                    "purchase_price": 50.0,
                    "analytic_distribution": {str(other_analytic.id): 100.0},
                }
            ],
        )

        sale.action_create_budget_control()

        key_accounts = {
            int(account_id)
            for key in sale.order_line.analytic_distribution
            for account_id in key.split(",")
        }
        self.assertEqual(key_accounts, {other_analytic.id, self.project.account_id.id})

    @freeze_time("2001-02-01")
    def test_12_new_sale_does_not_reopen_controlled_budget(self):
        """An approved control is changed only through an explicit reopen."""
        first_sale = self._create_sale_order(
            project=self.project,
            lines=[
                {
                    "product_id": self.product1.id,
                    "product_uom_qty": 1,
                    "price_unit": 150.0,
                    "purchase_price": 50.0,
                }
            ],
        )
        first_sale.action_confirm()
        control = first_sale.budget_control_id
        self.env["budget.control.line"].create(
            {
                "budget_control_id": control.id,
                "analytic_account_id": self.project.account_id.id,
                "template_line_id": self.template_line1.id,
                "date_from": self.budget_period.bm_date_from,
                "date_to": self.budget_period.bm_date_to,
                "amount": 50.0,
            }
        )
        control.action_submit()
        control.action_done()

        second_sale = self._create_sale_order(
            project=self.project,
            lines=[
                {
                    "product_id": self.product2.id,
                    "product_uom_qty": 1,
                    "price_unit": 200.0,
                    "purchase_price": 80.0,
                }
            ],
        )
        with self.assertRaisesRegex(UserError, "must be set to Draft"):
            second_sale.action_confirm()
        self.assertEqual(control.state, "done")
        self.assertNotIn(second_sale, control.sale_order_ids)

    @freeze_time("2001-02-01")
    def test_13_generated_project_creates_budget_control(self):
        """A project generated from a service line drives the SO budget."""
        sale = self._create_sale_order(
            lines=[
                {
                    "product_id": self.project_service.id,
                    "product_uom_qty": 2,
                    "price_unit": 200.0,
                    "purchase_price": 120.0,
                },
            ]
        )
        line = sale.order_line
        self.assertFalse(sale.project_id)
        self.assertFalse(line.project_id)
        with self.assertRaisesRegex(UserError, "Confirm the Sale Order first"):
            sale.action_create_budget_control()

        sale.action_confirm()

        self.assertTrue(line.project_id)
        self.assertEqual(sale.project_id, line.project_id)
        self.assertTrue(line.project_id.account_id)
        self.assertEqual(line.project_id.budget_control_scope, "lifetime")
        self.assertEqual(
            line.project_id.account_id.budget_control_scope,
            "lifetime",
        )
        self.assertTrue(sale.budget_control_id)
        self.assertEqual(sale.budget_control_id.budget_scope, "lifetime")
        self.assertEqual(
            sale.budget_control_id.budget_period_id.project_id,
            line.project_id,
        )
        self.assertEqual(
            sale.budget_control_id.budget_period_id.name,
            line.project_id.display_name,
        )
        self.assertEqual(
            sale.budget_control_id.analytic_account_id,
            line.project_id.account_id,
        )
        self.assertAlmostEqual(sale.budget_control_id.allocated_amount, 240.0)
        self.assertIn(sale, sale.budget_control_id.sale_order_ids)
        self.assertIn(
            str(line.project_id.account_id.id),
            line.analytic_distribution,
        )

    @freeze_time("2001-02-01")
    def test_14_one_sale_uses_one_lifetime_budget_across_years(self):
        """A one-off SO controls total Project cost across fiscal years."""
        sale = self._create_sale_order(
            lines=[
                {
                    "product_id": self.project_service.id,
                    "product_uom_qty": 1,
                    "price_unit": 700.0,
                    "purchase_price": 500.0,
                },
            ]
        )
        sale.action_confirm()
        project = sale.project_id
        control = sale.budget_control_id
        project_period = control.budget_period_id

        self.assertEqual(control.allocated_amount, 500.0)
        self.assertEqual(control.sale_price, 700.0)
        self.assertEqual(control.gross_profit, 200.0)
        with self.assertRaisesRegex(UserError, "Planned Start and End"):
            control.action_submit()

        project.write({"date_start": "2001-02-01", "date": "2002-12-31"})
        self.assertEqual(project_period.bm_date_from, fields.Date.to_date("2001-02-01"))
        self.assertEqual(project_period.bm_date_to, fields.Date.to_date("2002-12-31"))
        self.assertEqual(control.date_from, project.date_start)
        self.assertEqual(control.date_to, project.date)
        self.assertEqual(project.account_id.bm_date_from, project.date_start)
        self.assertEqual(project.account_id.bm_date_to, project.date)
        with self.assertRaisesRegex(UserError, "Change Project Lifetime dates"):
            project_period.write({"bm_date_to": "2003-12-31"})
        project_period.invalidate_recordset(["bm_date_to"])

        fiscal_2002 = self.budget_period.copy(
            {
                "name": "Budget for FY2002",
                "bm_date_from": "2002-01-01",
                "bm_date_to": "2002-12-31",
            }
        )
        project_period.control_budget = True
        self.env["budget.control.line"].create(
            {
                "budget_control_id": control.id,
                "analytic_account_id": project.account_id.id,
                "template_line_id": self.template_line1.id,
                "date_from": project.date_start,
                "date_to": project.date,
                "amount": 500.0,
            }
        )
        control.action_submit()
        control.action_done()

        BudgetPeriod = self.env["budget.period"]
        self.assertEqual(
            BudgetPeriod._get_eligible_budget_period("2002-06-01"), fiscal_2002
        )
        self.assertEqual(
            BudgetPeriod.with_context(
                budget_analytic_id=project.account_id.id
            )._get_eligible_budget_period("2002-06-01"),
            project_period,
        )

        bill = self._create_simple_bill(
            {str(project.account_id.id): 100}, self.account_kpi1, 400.0
        )
        bill.invoice_date = "2002-06-01"
        bill.action_post()
        self.assertEqual(
            bill.invoice_line_ids.budget_move_ids.date,
            fields.Date.to_date("2002-06-01"),
        )
        control.invalidate_recordset()
        self.assertAlmostEqual(control.amount_actual, 400.0)
        self.assertAlmostEqual(control.amount_balance, 100.0)

        excessive_bill = self._create_simple_bill(
            {str(project.account_id.id): 100}, self.account_kpi1, 101.0
        )
        excessive_bill.invoice_date = "2002-07-01"
        with self.assertRaisesRegex(UserError, "Budget not sufficient"):
            excessive_bill.action_post()

        with self.assertRaisesRegex(UserError, "Set Project Lifetime Budget Control"):
            project.write({"date_start": "2001-01-01", "date": "2003-12-31"})

    @freeze_time("2001-02-01")
    def test_15_generated_project_can_use_fiscal_scope(self):
        """Annual Project budgeting remains an explicit pre-confirm choice."""
        sale = self._create_sale_order(
            lines=[
                {
                    "product_id": self.project_service.id,
                    "product_uom_qty": 1,
                    "price_unit": 200.0,
                    "purchase_price": 120.0,
                },
            ]
        )
        self.assertTrue(sale.will_create_project)
        sale.generated_project_budget_scope = "fiscal"
        sale.action_confirm()

        self.assertEqual(sale.project_id.budget_control_scope, "fiscal")
        self.assertEqual(sale.project_id.account_id.budget_control_scope, "fiscal")
        self.assertEqual(sale.budget_control_id.budget_scope, "fiscal")
        self.assertEqual(sale.budget_control_id.budget_period_id, self.budget_period)

    @freeze_time("2001-02-01")
    def test_16_budget_user_can_create_lifetime_budget(self):
        """A Budget User can trigger the system-managed Lifetime period."""
        project = self.env["project.project"].create(
            {
                "name": "Lifetime Project",
                "account_id": self.costcenterX.id,
                "budget_control_scope": "lifetime",
                "date_start": "2001-01-01",
                "date": "2002-12-31",
            }
        )
        sale = self._create_sale_order(
            project=project,
            lines=[
                {
                    "product_id": self.product1.id,
                    "product_uom_qty": 1,
                    "price_unit": 100.0,
                    "purchase_price": 60.0,
                }
            ],
        )

        BudgetPeriod = self.env["budget.period"].with_user(self.budget_user)
        self.assertFalse(
            self.budget_user.has_group("budget_control.group_budget_control_manager")
        )
        with self.assertRaises(AccessError):
            BudgetPeriod.create(
                {
                    "name": "Unauthorized Period",
                    "bm_date_from": "2001-01-01",
                    "bm_date_to": "2001-12-31",
                }
            )

        self.assertTrue(sale.with_user(self.budget_user).action_create_budget_control())
        self.assertEqual(sale.budget_control_id.budget_scope, "lifetime")
        self.assertEqual(sale.budget_control_id.budget_period_id.project_id, project)
        self.assertEqual(project.account_id.budget_control_scope, "lifetime")
