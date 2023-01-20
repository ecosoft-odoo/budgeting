# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

from freezegun import freeze_time

from odoo.tests import tagged
from odoo.tests.common import Form

from odoo.addons.budget_activity.tests.test_budget_activity import TestBudgetActivity


@tagged("post_install", "-at_install")
class TestBudgetActivityPurchaseRequisition(TestBudgetActivity):
    @classmethod
    @freeze_time("2001-02-01")
    def setUpClass(cls):
        super().setUpClass()
        cls.pr_te_wiz = cls.env["purchase.request.line.make.purchase.requisition"]

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
                    line.analytic_account_id = pr_line["analytic_id"]
                    line.activity_id = pr_line["activity_id"]
        purchase_request = pr.save()
        return purchase_request

    @freeze_time("2001-02-01")
    def test_01_budget_activity_purchase_requisition(self):
        """
        On purchase requisition,
        - If no activity, budget follows product's account
        - If activity is selected, account follows activity's regardless of product
        """
        # Control budget
        self.budget_period.control_budget = True
        self.budget_control.action_done()

        purchase_request = self._create_purchase_request(
            [
                {
                    "product_id": self.product1,  # KPI1 = 30
                    "product_qty": 3,
                    "estimated_cost": 30,
                    "analytic_id": self.costcenter1,
                    "activity_id": self.activity3,
                },
            ]
        )
        purchase_request = purchase_request.with_context(
            force_date_commit=purchase_request.date_start
        )
        self.assertEqual(self.budget_control.amount_balance, 2400)
        purchase_request.button_to_approve()
        purchase_request.button_approved()
        # PR Commit = 30, PO Commit = 0, Balance = 2370
        self.assertEqual(self.budget_control.amount_purchase_request, 30)
        self.assertEqual(self.budget_control.amount_purchase, 0)
        self.assertEqual(self.budget_control.amount_balance, 2370)

        # Check create Agreement from PR, activity must be equal PR
        wiz = self.pr_te_wiz.with_context(
            active_model="purchase.request", active_ids=[purchase_request.id]
        ).create({})
        self.assertEqual(len(wiz.item_ids), 1)
        wiz.make_purchase_requisition()
        # Check PR link to TE must have 1
        self.assertEqual(purchase_request.requisition_count, 1)
        requisition = purchase_request.line_ids.requisition_lines.requisition_id
        # activity (TE Line) = activity (PR Line)
        self.assertEqual(
            purchase_request.line_ids.activity_id,
            requisition.line_ids.activity_id,
        )
        # Create Purchase from Agreement, activtiy must be equal Agreement
        purchase = self.env["purchase.order"].create(
            {
                "partner_id": self.env.ref("base.res_partner_12").id,
                "requisition_id": requisition.id,
            }
        )
        purchase._onchange_requisition_id()
        self.assertEqual(
            purchase.order_line.activity_id, requisition.line_ids.activity_id
        )
