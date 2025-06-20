# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from freezegun import freeze_time

from odoo.tests import Form, tagged

from odoo.addons.budget_activity_purchase_request.tests.test_budget_activity_purchase_request import (  # noqa: E501
    TestBudgetActivityPurchaseRequest,
)


@tagged("post_install", "-at_install")
class TestBudgetActivityPurchaseRequisition(TestBudgetActivityPurchaseRequest):
    @classmethod
    @freeze_time("2001-02-01")
    def setUpClass(cls):
        super().setUpClass()
        cls.pr_te_wiz = cls.env["purchase.request.line.make.purchase.requisition"]

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

        analytic_distribution = {self.costcenter1.id: 100}
        purchase_request = self._create_purchase_request(
            [
                {
                    "product_id": self.product1,  # KPI1 = 30
                    "product_qty": 3,
                    "estimated_cost": 30,
                    "analytic_distribution": analytic_distribution,
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
        # activity (PR Line) = activity (TE Line)
        self.assertEqual(
            purchase_request.line_ids.activity_id,
            requisition.line_ids.activity_id,
        )

        # Test change activity in Purchase Agreement and send it to PO
        requisition.line_ids.write({"activity_id": self.activity1.id})

        # Create Purchase from Agreement, activtiy must be equal Agreement
        purchase = self.env["purchase.order"].create(
            {
                "partner_id": self.env.ref("base.res_partner_12").id,
                "requisition_id": requisition.id,
            }
        )
        with Form(purchase) as p:
            p.requisition_id = requisition
        p.save()

        # activity (TE Line) = activity (PO Line)
        self.assertEqual(
            purchase.order_line.activity_id, requisition.line_ids.activity_id
        )

        # activity PO != activity PR
        self.assertNotEqual(
            purchase.order_line.activity_id, purchase_request.line_ids.activity_id
        )
