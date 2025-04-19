# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

from freezegun import freeze_time

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import Form, tagged

from odoo.addons.budget_control.tests.common import get_budget_common_class


@tagged("post_install", "-at_install")
class TestBudgetControlPurchase(get_budget_common_class()):
    @classmethod
    @freeze_time("2001-02-01")
    def setUpClass(cls):
        super().setUpClass()
        # Create budget plan with 1 analytic
        lines = [
            Command.create(
                {"analytic_account_id": cls.costcenter1.id, "amount": 2400.0}
            )
        ]
        cls.budget_plan = cls.create_budget_plan(
            cls,
            name="Test - Plan {cls.budget_period.name}",
            budget_period=cls.budget_period,
            lines=lines,
        )
        cls.budget_plan.action_confirm()
        cls.budget_plan.action_create_update_budget_control()
        cls.budget_plan.action_done()

        # Refresh data
        cls.budget_plan.invalidate_recordset()

        cls.budget_control = cls.budget_plan.budget_control_ids
        cls.budget_control.template_line_ids = [
            cls.template_line1.id,
            cls.template_line2.id,
            cls.template_line3.id,
        ]

        # Test item created for 3 kpi x 4 quarters = 12 budget items
        cls.budget_control.prepare_budget_control_matrix()
        assert len(cls.budget_control.line_ids) == 12
        # Assign budget.control amount: KPI1 = 100x4=400, KPI2=800, KPI3=1,200
        cls.budget_control.line_ids.filtered(lambda x: x.kpi_id == cls.kpi1).write(
            {"amount": 100}
        )
        cls.budget_control.line_ids.filtered(lambda x: x.kpi_id == cls.kpi2).write(
            {"amount": 200}
        )
        cls.budget_control.line_ids.filtered(lambda x: x.kpi_id == cls.kpi3).write(
            {"amount": 300}
        )

        # Purchase method
        cls.product1.product_tmpl_id.purchase_method = "purchase"
        cls.product2.product_tmpl_id.purchase_method = "purchase"

    @freeze_time("2001-02-01")
    def _create_purchase(self, po_lines):
        Purchase = self.env["purchase.order"]
        view_id = "purchase.purchase_order_form"
        with Form(Purchase, view=view_id) as po:
            po.partner_id = self.vendor
            po.date_order = datetime.today()
            for po_line in po_lines:
                with po.order_line.new() as line:
                    line.product_id = po_line["product_id"]
                    line.product_qty = po_line["product_qty"]
                    line.price_unit = po_line["price_unit"]
                    line.analytic_distribution = po_line["analytic_distribution"]
        purchase = po.save()
        return purchase

    @freeze_time("2001-02-01")
    def test_01_budget_purchase(self):
        """
        On Purchase Order
        (1) Test case, no budget check -> OK
        (2) Check Budget with analytic_kpi -> Error amount exceed on kpi1
        (3) Check Budget with analytic -> OK
        (2) Check Budget with analytic -> Error amount exceed
        """
        # Controlled budget
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.assertAlmostEqual(self.budget_control.amount_budget, 2400.0)
        # Prepare PO
        analytic_distribution = {str(self.costcenter1.id): 100}
        purchase = self._create_purchase(
            [
                {
                    "product_id": self.product1,  # KPI1 = 401 -> error
                    "product_qty": 1,
                    "price_unit": 401,
                    "analytic_distribution": analytic_distribution,
                },
                {
                    "product_id": self.product2,  # KPI2 = 798
                    "product_qty": 2,
                    "price_unit": 399,
                    "analytic_distribution": analytic_distribution,
                },
            ]
        )

        # (1) No budget check first
        self.budget_period.control_budget = False
        self.budget_period.control_level = "analytic_kpi"
        # force date commit, as freeze_time not work for write_date
        purchase = purchase.with_context(force_date_commit=purchase.date_order)
        purchase.button_confirm()  # No budget check no error
        self.assertTrue(purchase.budget_move_ids)

        # (2) Check Budget with analytic_kpi -> Error
        purchase.button_cancel()
        purchase.button_draft()
        self.budget_period.control_budget = True  # Set to check budget
        self.assertTrue(self.budget_period.purchase)
        # kpi 1 (kpi1) & CostCenter1, will result in $ -1.00
        with self.assertRaisesRegex(UserError, "Budget not sufficient"):
            purchase.button_confirm()
        # (3) Check Budget with analytic -> OK
        purchase.button_cancel()
        purchase.button_draft()
        self.budget_period.control_level = "analytic"
        purchase.button_confirm()

        self.assertAlmostEqual(
            self.budget_control.amount_balance, 1201.0
        )  # 2400 - (798 + 401)
        purchase.button_cancel()
        self.assertAlmostEqual(self.budget_control.amount_balance, 2400.0)
        # (4) Change amount from 2 * 399 to 2 * 1000
        purchase.order_line[1].price_unit = 1000
        purchase.button_draft()
        # CostCenter1, will result in $ -1.00
        with self.assertRaises(UserError):
            purchase.button_confirm()

    @freeze_time("2001-02-01")
    def test_02_budget_purchase_no_control(self):
        # Controlled budget
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.assertAlmostEqual(self.budget_control.amount_budget, 2400.0)

        self.budget_period.control_budget = True
        self.assertTrue(self.budget_period.purchase)
        self.assertEqual(self.budget_period.control_level, "analytic_kpi")

        # Prepare PO
        analytic_distribution = {str(self.costcenter1.id): 100}
        purchase = self._create_purchase(
            [
                {
                    "product_id": self.product1,  # KPI1 = 401 -> error
                    "product_qty": 1,
                    "price_unit": 401,
                    "analytic_distribution": analytic_distribution,
                },
                {
                    "product_id": self.product2,  # KPI2 = 798
                    "product_qty": 2,
                    "price_unit": 399,
                    "analytic_distribution": analytic_distribution,
                },
            ]
        )
        purchase = purchase.with_context(force_date_commit=purchase.date_order)

        # kpi 1 (kpi1) & CostCenter1, will result in $ -1.00
        with self.assertRaisesRegex(UserError, "Budget not sufficient"):
            purchase.button_confirm()

        # Not control purchase (specific)
        self.budget_period.purchase = False
        purchase.button_confirm()

    @freeze_time("2001-02-01")
    def test_03_budget_purchase_to_invoice(self):
        """Purchase to Invoice, commit and uncommit"""
        # Controlled budget
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.assertAlmostEqual(self.budget_control.amount_budget, 2400.0)

        # Prepare PO on kpi1 with qty 4 and unit_price 600
        analytic_distribution = {str(self.costcenter1.id): 100}
        purchase = self._create_purchase(
            [
                {
                    "product_id": self.product1,  # KPI1 = 2400
                    "product_qty": 4,
                    "price_unit": 600,
                    "analytic_distribution": analytic_distribution,
                },
            ]
        )
        self.budget_period.control_budget = True
        self.budget_period.control_level = "analytic"
        purchase = purchase.with_context(force_date_commit=purchase.date_order)
        purchase.button_confirm()
        # PO Commit = 2400, INV Actual = 0, Balance = 0
        self.assertAlmostEqual(self.budget_control.amount_commit, 2400.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 0.0)
        # Create and post invoice
        purchase.action_create_invoice()
        self.assertEqual(purchase.invoice_status, "invoiced")
        invoice = purchase.invoice_ids[:1]
        # Change qty to 1
        invoice.with_context(check_move_validity=False).invoice_line_ids[0].quantity = 1
        invoice.invoice_date = invoice.date
        invoice.action_post()
        # PO Commit = 1800, INV Actual = 600, Balance = 0
        self.assertAlmostEqual(self.budget_control.amount_commit, 1800.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 600.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 0.0)
        # Cancel invoice
        invoice.button_cancel()
        self.assertAlmostEqual(self.budget_control.amount_commit, 2400.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 0.0)

    @freeze_time("2001-02-01")
    def test_03_budget_recompute_and_close_budget_move(self):
        """Purchase to Invoice (partial)
        - Test recompute on both Purchase and Invoice
        - Test close on both Purchase and Invoice"""
        # Controlled budget
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.assertAlmostEqual(self.budget_control.amount_budget, 2400.0)

        analytic_distribution = {str(self.costcenter1.id): 100}
        purchase = self._create_purchase(
            [
                {
                    "product_id": self.product1,  # KPI1 = 300
                    "product_qty": 2,
                    "price_unit": 150,
                    "analytic_distribution": analytic_distribution,
                },
                {
                    "product_id": self.product2,  # KPI2 = 400
                    "product_qty": 4,
                    "price_unit": 100,
                    "analytic_distribution": analytic_distribution,
                },
            ]
        )
        self.budget_period.control_budget = True
        self.budget_period.control_level = "analytic"
        purchase = purchase.with_context(force_date_commit=purchase.date_order)
        purchase.button_confirm()
        # PO Commit = 700, INV Actual = 0
        self.assertAlmostEqual(self.budget_control.amount_purchase, 700.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 0.0)
        # Create and post invoice
        purchase.action_create_invoice()
        self.assertEqual(purchase.invoice_status, "invoiced")
        invoice = purchase.invoice_ids[:1]
        # Change qty to 1 and 3
        invoice = invoice.with_context(check_move_validity=False)
        invoice.invoice_line_ids[0].quantity = 1
        invoice.invoice_line_ids[1].quantity = 3
        invoice.invoice_date = invoice.date
        invoice.action_post()
        # PO Commit = 700-450 = 250.0 , INV Actual = (1*150) + (3*100) = 450.0
        self.assertAlmostEqual(self.budget_control.amount_purchase, 250.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 450.0)
        # Test recompute, must be same
        purchase.recompute_budget_move()
        self.assertAlmostEqual(self.budget_control.amount_purchase, 250.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 450.0)
        invoice.recompute_budget_move()
        self.assertAlmostEqual(self.budget_control.amount_purchase, 250.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 450.0)
        # Test close budget move
        purchase.close_budget_move()
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_purchase, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 450.0)
        # Test close budget move
        invoice.close_budget_move()
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_purchase, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 0.0)
