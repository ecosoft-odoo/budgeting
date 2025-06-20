# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from freezegun import freeze_time

from odoo.tests import Form, tagged

from odoo.addons.budget_plan_detail_purchase_request.tests.test_budget_plan_detail_purchase_request import (  # noqa: E501
    TestBudgetPlanDetailPurchaseRequest,
)


@tagged("post_install", "-at_install")
class TestBudgetPlanDetailPurchaseRequisition(TestBudgetPlanDetailPurchaseRequest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pr_te_wiz = cls.env["purchase.request.line.make.purchase.requisition"]

    @freeze_time("2001-02-01")
    def test_01_commitment_purchase_request_to_requisition(self):
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
                    "estimated_cost": 400.0,
                    "analytic_distribution": analytic_distribution,
                },
            ]
        )

        # Add fund1, tags1 in purchase request line
        purchase_request.line_ids.fund_id = self.fund1_g1.id
        purchase_request.line_ids.analytic_tag_ids = [(4, self.analytic_tag1.id)]

        # force date commit, as freeze_time not work for write_date
        purchase_request = purchase_request.with_context(
            force_date_commit=purchase_request.date_start
        )
        self.assertAlmostEqual(budget_control.amount_balance, 2400.0)

        purchase_request.button_to_approve()
        purchase_request.button_approved()

        self.assertEqual(purchase_request.budget_move_ids.fund_id, self.fund1_g1)
        self.assertEqual(
            purchase_request.budget_move_ids.analytic_tag_ids, self.analytic_tag1
        )
        self.assertAlmostEqual(budget_control.amount_purchase_request, 400.0)
        self.assertAlmostEqual(budget_control.amount_purchase, 0.0)
        self.assertAlmostEqual(budget_control.amount_balance, 2000.0)

        # Create Purchase Agreement from PR
        wiz = self.pr_te_wiz.with_context(
            active_model="purchase.request", active_ids=[purchase_request.id]
        ).create({})
        self.assertEqual(len(wiz.item_ids), 1)
        wiz.make_purchase_requisition()

        # Check PR link to Purchase Agreement must have 1
        self.assertEqual(purchase_request.requisition_count, 1)
        requisition = purchase_request.line_ids.requisition_lines.requisition_id

        # Check value (Fund, Analytic Tags) should be send from PR to Purchase Agreement
        self.assertEqual(
            purchase_request.line_ids.fund_id,
            requisition.line_ids.fund_id,
        )
        self.assertEqual(
            purchase_request.line_ids.analytic_tag_ids,
            requisition.line_ids.analytic_tag_ids,
        )

        # Test change fund, analytic tags in Purchase Agreement and send it to PO
        requisition.line_ids.write(
            {"fund_id": self.fund2_g1.id, "analytic_tag_ids": []}
        )
        # Create Purchase from Agreement, activtiy must be equal Agreement
        purchase = self.env["purchase.order"].create(
            {
                "partner_id": self.env.ref("base.res_partner_12").id,
            }
        )
        with Form(purchase) as p:
            p.requisition_id = requisition
        p.save()

        self.assertEqual(purchase.order_line.fund_id, requisition.line_ids.fund_id)
        self.assertEqual(
            purchase.order_line.analytic_tag_ids, requisition.line_ids.analytic_tag_ids
        )
        # PO != PR
        self.assertNotEqual(
            purchase.order_line.fund_id, purchase_request.line_ids.fund_id
        )
        self.assertEqual(
            purchase.order_line.analytic_tag_ids,
            purchase_request.line_ids.analytic_tag_ids,
        )
