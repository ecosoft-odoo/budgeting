# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

from freezegun import freeze_time

from odoo.exceptions import UserError
from odoo.tests import Form, tagged

from odoo.addons.budget_activity.tests.test_budget_activity import TestBudgetActivity


@tagged("post_install", "-at_install")
class TestBudgetActivityPurchaseRequest(TestBudgetActivity):
    @classmethod
    @freeze_time("2001-02-01")
    def setUpClass(cls):
        super().setUpClass()
        cls.product1.product_tmpl_id.purchase_method = "purchase"

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
                    line.activity_id = pr_line["activity_id"]
        purchase_request = pr.save()
        return purchase_request

    @freeze_time("2001-02-01")
    def test_01_budget_activity_purchase_request_control_analytic(self):
        """
        On purchase request,
        - If no activity, budget follows product's account
        - If activity is selected, account follows activity's regardless of product
        """
        self.budget_period.control_level = "analytic"
        self.assertEqual(self.budget_period.control_level, "analytic")

        # KPI1=400, KPI2=800, KPI3=1,200
        analytic_distribution = {str(self.costcenter1.id): 100}
        purchase_request = self._create_purchase_request(
            [
                {
                    "product_id": self.product1,  # KPI1
                    "product_qty": 3,
                    "estimated_cost": 1201,
                    "analytic_distribution": analytic_distribution,
                    "activity_id": self.activity3,
                },
            ]
        )
        purchase_request = purchase_request.with_context(
            force_date_commit=purchase_request.date_start
        )
        self.assertEqual(self.budget_control.amount_balance, 2400)

        # Can commit budget because control level analytic (2400.0)
        purchase_request.button_to_approve()
        purchase_request.button_approved()

        # PR Commit = 1201, PO Commit = 0, Balance = 1199
        self.assertAlmostEqual(self.budget_control.amount_purchase_request, 1201.0)
        self.assertAlmostEqual(self.budget_control.amount_purchase, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 1199.0)
        self.assertEqual(
            purchase_request.budget_move_ids.account_id,
            purchase_request.line_ids.activity_id.account_id,
        )
        self.assertEqual(
            purchase_request.budget_move_ids.activity_id,
            purchase_request.line_ids.activity_id,
        )

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
        # Check activity in po line must equal pr line
        self.assertEqual(
            purchase.order_line.activity_id, purchase_request.line_ids.activity_id
        )

        purchase = purchase.with_context(force_date_commit=purchase.date_order)
        purchase.order_line.price_unit = 200.0
        purchase.button_confirm()

        # PR Commit = 0, PO Commit = 200*3=600, Balance = 2200
        self.assertAlmostEqual(self.budget_control.amount_purchase_request, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_purchase, 600.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 1800.0)
        self.assertEqual(
            purchase.budget_move_ids.account_id,
            purchase.order_line.activity_id.account_id,
        )
        self.assertEqual(
            purchase.budget_move_ids.activity_id,
            purchase.order_line.activity_id,
        )

    @freeze_time("2001-02-01")
    def test_02_budget_activity_purchase_request_control_analytic_kpi(self):
        """
        On purchase request,
        - If no activity, budget follows product's account
        - If activity is selected, account follows activity's regardless of product
        """
        self.budget_period.control_level = "analytic_kpi"
        self.assertEqual(self.budget_period.control_level, "analytic_kpi")

        # KPI1=400, KPI2=800, KPI3=1,200
        analytic_distribution = {str(self.costcenter1.id): 100}
        purchase_request = self._create_purchase_request(
            [
                {
                    "product_id": self.product1,  # KPI1
                    "product_qty": 3,
                    "estimated_cost": 1201,
                    "analytic_distribution": analytic_distribution,
                    "activity_id": self.activity3,
                },
            ]
        )
        purchase_request = purchase_request.with_context(
            force_date_commit=purchase_request.date_start
        )
        self.assertEqual(self.budget_control.amount_balance, 2400)

        # Can't commit budget because control level analytic&kpi (1200.0)
        with self.assertRaisesRegex(UserError, "Budget not sufficient"):
            purchase_request.button_to_approve()
        purchase_request.button_draft()

        purchase_request.line_ids.estimated_cost = 1000.0
        purchase_request.button_to_approve()
        purchase_request.button_approved()

        # PR Commit = 1000, PO Commit = 0, Balance = 1400
        self.assertAlmostEqual(self.budget_control.amount_purchase_request, 1000.0)
        self.assertAlmostEqual(self.budget_control.amount_purchase, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 1400.0)
        self.assertEqual(
            purchase_request.budget_move_ids.account_id,
            purchase_request.line_ids.activity_id.account_id,
        )
        self.assertEqual(
            purchase_request.budget_move_ids.activity_id,
            purchase_request.line_ids.activity_id,
        )

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
        # Check activity in po line must equal pr line
        self.assertEqual(
            purchase.order_line.activity_id, purchase_request.line_ids.activity_id
        )

        purchase = purchase.with_context(force_date_commit=purchase.date_order)
        purchase.order_line.price_unit = 200.0
        purchase.button_confirm()

        # PR Commit = 0, PO Commit = 3*200=600, Balance = 2200
        self.assertAlmostEqual(self.budget_control.amount_purchase_request, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_purchase, 600.0)
        self.assertAlmostEqual(self.budget_control.amount_balance, 1800.0)
        self.assertEqual(
            purchase.budget_move_ids.account_id,
            purchase.order_line.activity_id.account_id,
        )
        self.assertEqual(
            purchase.budget_move_ids.activity_id,
            purchase.order_line.activity_id,
        )
