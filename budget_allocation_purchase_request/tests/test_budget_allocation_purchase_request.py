# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

from freezegun import freeze_time

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import Form

from odoo.addons.budget_allocation.tests.test_budget_allocation import (
    TestBudgetAllocation,
)


@tagged("post_install", "-at_install")
class TestBudgetAllocationPurchaseRequest(TestBudgetAllocation):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # # Purchase method
        # cls.product1.product_tmpl_id.purchase_method = "purchase"

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
        purchase_request = pr.save()
        return purchase_request

    @freeze_time("2001-02-01")
    def test_01_commitment_purchase_request_fund(self):
        """Create same analytic, difference fund, difference analytic tags
        line 1: Costcenter1, Fund1, Tag1, 50.0
        line 2: Costcenter1, Fund1, Tag2, 100.0
        line 3: Costcenter1, Fund2,     , 100.0
        line 4: CostcenterX, Fund1,     , 100.0
        """
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
        # Commit purchase without allocation (no fund, no tags)
        purchase_request = self._create_purchase_request(
            [
                {
                    "product_id": self.product1,
                    "product_qty": 3,
                    "estimated_cost": 30,
                    "analytic_id": self.costcenter1,
                },
            ]
        )
        # force date commit, as freeze_time not work for write_date
        purchase_request = purchase_request.with_context(
            force_date_commit=purchase_request.date_start
        )
        self.assertEqual(budget_control.amount_balance, 250)
        # Not allocated in budget allocation
        with self.assertRaises(UserError):
            purchase_request.button_to_approve()
        # Add fund1, tags1 in expense line
        purchase_request.line_ids.fund_id = self.fund1_g1.id
        purchase_request.line_ids.analytic_tag_ids = [(4, self.analytic_tag1.id)]
        purchase_request.button_to_approve()
        purchase_request.button_approved()
        # PR Commit = 30, PO Commit = 0, Balance = 270
        self.assertEqual(budget_control.amount_purchase_request, 30)
        self.assertEqual(budget_control.amount_purchase, 0)
        self.assertEqual(budget_control.amount_balance, 220)
        # Create PR from PO
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
        # Check quantity, fund and analytic tags of purchase
        self.assertEqual(purchase.order_line[0].product_qty, 3)
        self.assertEqual(purchase.order_line[0].fund_id, self.fund1_g1)
        self.assertEqual(purchase.order_line[0].analytic_tag_ids, self.analytic_tag1)
