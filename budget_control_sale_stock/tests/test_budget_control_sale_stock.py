# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from freezegun import freeze_time

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged

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
        # Project linked to costcenter1 analytic account
        cls.project = cls.env["project.project"].create(
            {
                "name": "Test Sales Project",
                "account_id": cls.costcenter1.id,
            }
        )
        # Analytic plan for sale budget (used when SO has no project)
        cls.sale_plan = cls.AnalyticPlan.create({"name": "Sale Budget Plan"})

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
