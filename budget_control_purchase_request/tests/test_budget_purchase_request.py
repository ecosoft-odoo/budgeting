# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

from freezegun import freeze_time

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import Form, tagged

from odoo.addons.budget_control.tests.common import get_budget_common_class


@tagged("post_install", "-at_install")
class TestBudgetControlPurchaseRequest(get_budget_common_class()):
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

        # # Purchase method
        # cls.product1.product_tmpl_id.purchase_method = "purchase"
        # cls.product2.product_tmpl_id.purchase_method = "purchase"

    @freeze_time("2001-02-01")
    def _create_purchase_request(self, pr_lines):
        PurchaseRequest = self.env["purchase.request"]
        view_id = "purchase_request.view_purchase_request_form"
        with Form(PurchaseRequest, view=view_id) as pr:
            pr.date_start = datetime.today()
            for pr_line in pr_lines:
                with pr.line_ids.new() as line:
                    line.product_id = pr_line["product_id"]
                    line.product_qty = pr_line["product_qty"]
                    line.estimated_cost = pr_line["estimated_cost"]
                    line.analytic_distribution = pr_line["analytic_distribution"]
        purchase_request = pr.save()
        return purchase_request

    @freeze_time("2001-02-01")
    def test_01_budget_purchase_request(self):
        """
        On Purchase Request
        (1) Test case, no budget check -> OK
        (2) Check Budget with analytic_kpi -> Error amount exceed on kpi1
        (3) Check Budget with analytic -> OK
        (2) Check Budget with analytic -> Error amount exceed
        """
        # Controlled budget
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.assertAlmostEqual(self.budget_control.amount_budget, 2400.0)

        # Prepare PR
        analytic_distribution = {str(self.costcenter1.id): 100}
        purchase_request = self._create_purchase_request(
            [
                {
                    "product_id": self.product1,  # KPI1 = 401 -> error
                    "product_qty": 1,
                    "estimated_cost": 401,
                    "analytic_distribution": analytic_distribution,
                },
                {
                    "product_id": self.product2,  # KPI2 = 798
                    "product_qty": 2,
                    "estimated_cost": 798,  # This is the price of qty 2
                    "analytic_distribution": analytic_distribution,
                },
            ]
        )
        # (1) No budget check first
        self.budget_period.control_budget = False
        self.budget_period.control_level = "analytic_kpi"
        # force date commit, as freeze_time not work for write_date
        purchase_request = purchase_request.with_context(
            force_date_commit=purchase_request.date_start
        )
        purchase_request.button_to_approve()
        purchase_request.button_approved()  # No budget check no error
        self.assertTrue(purchase_request.budget_move_ids)

        # (2) Check Budget with analytic_kpi -> Error
        purchase_request.button_draft()
        self.assertAlmostEqual(self.budget_control.amount_budget, 2400.0)
        self.budget_period.control_budget = True  # Set to check budget
        # kpi 1 (kpi1) & CostCenter1, will result in $ -1.00
        with self.assertRaisesRegex(UserError, "Budget not sufficient"):
            purchase_request.button_to_approve()
        purchase_request.button_draft()

        # (3) Check Budget with analytic -> OK
        self.budget_period.control_level = "analytic"
        purchase_request.button_to_approve()
        purchase_request.button_approved()
        self.assertAlmostEqual(
            self.budget_control.amount_balance, 1201.0
        )  # 2400-1199 = 1201
        purchase_request.button_draft()
        self.assertAlmostEqual(self.budget_control.amount_balance, 2400.0)

        # (4) Amount exceed -> Error
        purchase_request.line_ids.write({"estimated_cost": 1200.5})  # Total is 2401.0
        # CostCenter1, will result in $ -1.00
        with self.assertRaises(UserError):
            purchase_request.button_to_approve()

    @freeze_time("2001-02-01")
    def test_02_budget_pr_to_po(self):
        """PR to PO normally don't care about Quantity, it will uncommit all"""
        # Controlled budget
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.assertAlmostEqual(self.budget_control.amount_budget, 2400.0)

        # Prepare PR
        analytic_distribution = {str(self.costcenter1.id): 100}
        purchase_request = self._create_purchase_request(
            [
                {
                    "product_id": self.product1,  # KPI1 = 2000
                    "product_qty": 3,
                    "estimated_cost": 2000.0,
                    "analytic_distribution": analytic_distribution,
                },
            ]
        )
        # Check budget as analytic
        self.budget_period.control_budget = True
        self.budget_period.purchase = True
        self.budget_period.control_level = "analytic"

        purchase_request = purchase_request.with_context(
            force_date_commit=purchase_request.date_start
        )
        purchase_request.button_to_approve()
        purchase_request.button_approved()  # No budget check no error
        # PR Commit = 30, PO Commit = 0, Balance = 270
        self.assertAlmostEqual(self.budget_control.amount_purchase_request, 2000.0)
        self.assertAlmostEqual(self.budget_control.amount_purchase, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 400.0)

        # Create PO from PR
        MakePO = self.env["purchase.request.line.make.purchase.order"]
        view_id = "purchase_request.view_purchase_request_line_make_purchase_order"
        ctx = {
            "active_model": "purchase.request",
            "active_ids": [purchase_request.id],
        }
        with Form(MakePO.with_context(**ctx), view=view_id) as w:
            w.supplier_id = self.vendor
        wizard = w.save()
        res = wizard.make_purchase_order()
        purchase = self.env["purchase.order"].search(res["domain"])
        # Change quantity and price_unit of purchase
        self.assertEqual(purchase.order_line[0].product_qty, 3)
        purchase.order_line[0].product_qty = 2
        purchase.order_line[0].price_unit = 25
        purchase = purchase.with_context(force_date_commit=purchase.date_order)
        purchase.button_confirm()
        # PR will return all, PR Commit = 0, PO Commit = 50, Balance = 2350
        self.assertAlmostEqual(self.budget_control.amount_purchase_request, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_purchase, 50.0)
        self.assertAlmostEqual(
            self.budget_control.amount_balance, 2350.0
        )  # 2400-50 = 2350
        # Cancel PO
        purchase.button_cancel()
        self.assertAlmostEqual(self.budget_control.amount_purchase_request, 2000.0)
        self.assertAlmostEqual(self.budget_control.amount_purchase, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 400.0)

    @freeze_time("2001-02-01")
    def test_03_budget_recompute_and_close_budget_move(self):
        """PR to PO (partial PO, but PR will return all)
        - Test recompute on both PR and PO
        - Test close on both PR and PO"""
        # Controlled budget
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.assertAlmostEqual(self.budget_control.amount_budget, 2400.0)

        # Prepare PR
        analytic_distribution = {str(self.costcenter1.id): 100}
        purchase_request = self._create_purchase_request(
            [
                {
                    "product_id": self.product1,  # KPI1 = 300
                    "product_qty": 2,
                    "estimated_cost": 300,
                    "analytic_distribution": analytic_distribution,
                },
                {
                    "product_id": self.product2,  # KPI2 = 400
                    "product_qty": 4,
                    "estimated_cost": 400,
                    "analytic_distribution": analytic_distribution,
                },
            ]
        )
        # Check budget as analytic
        self.budget_period.control_budget = True
        self.budget_period.purchase = True
        self.budget_period.control_level = "analytic"
        purchase_request = purchase_request.with_context(
            force_date_commit=purchase_request.date_start
        )
        purchase_request.button_to_approve()
        purchase_request.button_approved()
        # PR Commit = 30, PO Commit = 0, Balance = 270
        self.assertAlmostEqual(self.budget_control.amount_purchase_request, 700.0)
        self.assertAlmostEqual(self.budget_control.amount_purchase, 0.0)
        # Create PO from PR
        MakePO = self.env["purchase.request.line.make.purchase.order"]
        view_id = "purchase_request.view_purchase_request_line_make_purchase_order"
        ctx = {
            "active_model": "purchase.request",
            "active_ids": [purchase_request.id],
        }
        with Form(MakePO.with_context(**ctx), view=view_id) as w:
            w.supplier_id = self.vendor
        wizard = w.save()
        res = wizard.make_purchase_order()
        purchase = self.env["purchase.order"].search(res["domain"])
        # Change quantity and price_unit of purchase, to commit only
        purchase.order_line[0].write({"product_qty": 1, "price_unit": 15})
        purchase.order_line[1].write({"product_qty": 3, "price_unit": 10})
        purchase = purchase.with_context(force_date_commit=purchase.date_order)
        purchase.button_confirm()
        # PR will return all, PR Commit = 0, PO Commit = 45
        self.assertAlmostEqual(self.budget_control.amount_purchase_request, 0)
        self.assertAlmostEqual(self.budget_control.amount_purchase, 45)
        self.assertAlmostEqual(self.budget_control.amount_balance, 2355.0)
        # Recompute PR and PO, should be the same.
        purchase_request.recompute_budget_move()
        self.assertAlmostEqual(self.budget_control.amount_purchase_request, 0)
        self.assertAlmostEqual(self.budget_control.amount_purchase, 45)
        self.assertAlmostEqual(self.budget_control.amount_balance, 2355.0)
        purchase.recompute_budget_move()
        self.assertAlmostEqual(self.budget_control.amount_purchase_request, 0)
        self.assertAlmostEqual(self.budget_control.amount_purchase, 45)
        self.assertAlmostEqual(self.budget_control.amount_balance, 2355.0)
        # Close budget
        purchase_request.close_budget_move()
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_purchase_request, 0)
        self.assertAlmostEqual(self.budget_control.amount_purchase, 45)
        self.assertAlmostEqual(self.budget_control.amount_balance, 2355.0)
        purchase.close_budget_move()
        self.budget_control.invalidate_recordset()
        self.assertAlmostEqual(self.budget_control.amount_purchase_request, 0)
        self.assertAlmostEqual(self.budget_control.amount_purchase, 0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 2400.0)
