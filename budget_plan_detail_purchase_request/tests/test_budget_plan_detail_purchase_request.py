# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

from freezegun import freeze_time

from odoo.exceptions import UserError
from odoo.tests import Form, tagged

from odoo.addons.budget_plan_detail.tests.test_budget_plan_detail import (
    TestBudgetPlanDetail,
)


@tagged("post_install", "-at_install")
class TestBudgetPlanDetailPurchaseRequest(TestBudgetPlanDetail):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

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
                    if pr_line.get("fund_id"):
                        line.fund_id = pr_line["fund_id"]
                    if pr_line.get("analytic_tag_ids"):
                        line.analytic_tag_ids = pr_line["analytic_tag_ids"]
        purchase_request = pr.save()
        return purchase_request

    @freeze_time("2001-02-01")
    def test_01_budget_plan_check_over_limit_purchase(self):
        """Create same analytic, difference fund, difference analytic tags
        line 1: Costcenter1, Fund1, Tag1, 600.0
        line 2: Costcenter1, Fund1, Tag2, 600.0
        line 3: Costcenter1, Fund2, Tag1, 600.0
        line 4: Costcenter1, Fund2,     , 600.0
        line 5: CostcenterX, Fund1, Tag1, 600.0
        line 6: CostcenterX, Fund2, Tag1, 600.0
        line 7: CostcenterX, Fund2, Tag2, 600.0
        line 8: CostcenterX, Fund1,     , 600.0
        """
        self._create_budget_plan_line_detail(self.budget_plan)
        self.budget_plan.action_confirm_plan_detail()
        self.budget_plan.action_confirm()
        self.assertEqual(self.budget_plan.state, "confirm")
        self.budget_plan.action_create_update_budget_control()
        self.budget_plan.action_done()

        self.assertEqual(self.budget_plan.state, "done")

        # Refresh data and Prepare budget control
        self.budget_plan.invalidate_recordset()
        # Get 1 budget control, Costcenter1 has 4 plan detail
        budget_control = self.budget_plan.budget_control_ids[0]
        budget_control.template_line_ids = [
            self.template_line1.id,
            self.template_line2.id,
            self.template_line3.id,
        ]

        # Test item created for 3 kpi x 4 quarters = 12 budget items
        budget_control.prepare_budget_control_matrix()
        assert len(budget_control.line_ids) == 12
        # Costcenter1 has 3 plan detail
        # Assign budget.control amount: KPI1 = 1500, 500, 400
        bc_items = budget_control.line_ids.filtered(lambda x: x.kpi_id == self.kpi1)
        bc_items[0].write({"amount": 1500})
        bc_items[1].write({"amount": 500})
        bc_items[2].write({"amount": 400})

        self.assertEqual(
            budget_control.mapped("plan_line_detail_ids"),
            self.budget_plan.line_detail_ids.filtered(
                lambda line: line.budget_control_id == budget_control
            ),
        )

        # Control budget
        budget_control.action_submit()
        budget_control.action_done()
        self.budget_period.control_budget = True

        # We allocate budget to Costcenter1 each 600.0 (total is 2400.0)
        analytic_distribution = {self.costcenter1.id: 100}

        # Commit purchase without allocation (no fund, no tags)
        purchase_request = self._create_purchase_request(
            [
                {
                    "product_id": self.product1,
                    "product_qty": 4,
                    "estimated_cost": 601.0,
                    "analytic_distribution": analytic_distribution,
                },
            ]
        )
        # force date commit, as freeze_time not work for write_date
        purchase_request = purchase_request.with_context(
            force_date_commit=purchase_request.date_start
        )
        self.assertAlmostEqual(budget_control.amount_balance, 2400.0)

        with self.assertRaisesRegex(
            UserError, "is not allocated on budget plan detail"
        ):
            purchase_request.button_to_approve()
        purchase_request.button_draft()

        # Add fund1, tags1 in purchase request line
        purchase_request.line_ids.fund_id = self.fund1_g1.id
        purchase_request.line_ids.analytic_tag_ids = [(4, self.analytic_tag1.id)]

        # Purchase Request commit amount 601 > allocated amount 600.0, it should error
        with self.assertRaisesRegex(
            UserError, "spend amount over budget plan detail limit"
        ):
            purchase_request.button_to_approve()
        purchase_request.button_draft()

        purchase_request.line_ids.estimated_cost = 400.0
        purchase_request.button_to_approve()
        purchase_request.button_approved()

        self.assertEqual(purchase_request.budget_move_ids.fund_id, self.fund1_g1)
        self.assertEqual(
            purchase_request.budget_move_ids.analytic_tag_ids, self.analytic_tag1
        )
        self.assertAlmostEqual(budget_control.amount_purchase_request, 400.0)
        self.assertAlmostEqual(budget_control.amount_purchase, 0.0)
        self.assertAlmostEqual(budget_control.amount_balance, 2000.0)

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
        wizard.make_purchase_order()

        po_line = purchase_request.line_ids.purchase_lines
        self.assertTrue(po_line)
        # Check quantity, fund and analytic tags of purchase
        self.assertEqual(po_line.product_qty, 4)
        self.assertEqual(po_line.fund_id, self.fund1_g1)
        self.assertEqual(po_line.analytic_tag_ids, self.analytic_tag1)

        # Commit PO 151.0 * 4 = 604.0, it should error
        po_line.price_unit = 151.0

        purchase = po_line.order_id

        with self.assertRaisesRegex(
            UserError, "spend amount over budget plan detail limit"
        ):
            purchase.button_confirm()
        purchase.button_draft()

        # Commit PO more than PR, it should return PR to 0.0 and PO commit 600.0
        po_line.price_unit = 150.0
        purchase.button_confirm()

        self.assertAlmostEqual(budget_control.amount_purchase_request, 0.0)
        self.assertAlmostEqual(budget_control.amount_purchase, 600.0)
        self.assertAlmostEqual(budget_control.amount_balance, 1800.0)
