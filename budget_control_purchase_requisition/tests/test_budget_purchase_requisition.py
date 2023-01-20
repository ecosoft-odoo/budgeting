# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

from freezegun import freeze_time

from odoo.tests import tagged
from odoo.tests.common import Form

from odoo.addons.budget_control.tests.common import BudgetControlCommon


@tagged("post_install", "-at_install")
class TestBudgetControlPurchaseRequisition(BudgetControlCommon):
    @classmethod
    @freeze_time("2001-02-01")
    def setUpClass(cls):
        super().setUpClass()
        cls.pr_te_wiz = cls.env["purchase.request.line.make.purchase.requisition"]
        cls.BudgetCommit = cls.env["budget.commit.forward"]
        # Create budget.period for next year
        cls.next_year = cls.year + 1
        cls.next_budget_period = cls.env["budget.period"].create(
            {
                "name": "Budget for FY%s" % cls.next_year,
                "template_id": cls.budget_period.template_id.id,
                "bm_date_from": "%s-01-01" % cls.next_year,
                "bm_date_to": "%s-12-31" % cls.next_year,
                "plan_date_range_type_id": cls.date_range_type.id,
                "control_level": "analytic_kpi",
            }
        )
        # Create sample ready to use Budget Control
        cls.budget_control = cls.BudgetControl.create(
            {
                "name": "CostCenter1/%s" % cls.year,
                "template_id": cls.budget_period.template_id.id,
                "budget_period_id": cls.budget_period.id,
                "analytic_account_id": cls.costcenter1.id,
                "plan_date_range_type_id": cls.date_range_type.id,
                "template_line_ids": [
                    cls.template_line1.id,
                    cls.template_line2.id,
                    cls.template_line3.id,
                ],
            }
        )
        # Test item created for 3 kpi x 4 quarters = 12 budget items
        cls.budget_control.prepare_budget_control_matrix()
        assert len(cls.budget_control.line_ids) == 12
        # Assign budget.control amount: KPI1 = 100, KPI2=800, Total=300
        cls.budget_control.line_ids.filtered(lambda x: x.kpi_id == cls.kpi1)[:1].write(
            {"amount": 100}
        )
        cls.budget_control.line_ids.filtered(lambda x: x.kpi_id == cls.kpi2)[:1].write(
            {"amount": 200}
        )
        cls.budget_control.flush()  # Need to flush data into table, so it can be sql
        cls.budget_control.allocated_amount = 300
        cls.budget_control.action_done()

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
    def test_01_budget_pr_to_te(self):
        """Test analytic account in TE must be from forward analytic account (if any)"""
        # KPI1 = 100, KPI2 = 200, Total = 300
        self.assertEqual(300, self.budget_control.amount_budget)
        # Prepare PR
        purchase_request = self._create_purchase_request(
            [
                {
                    "product_id": self.product1,  # KPI1 = 30
                    "product_qty": 3,
                    "estimated_cost": 30,
                    "analytic_id": self.costcenter1,
                },
            ]
        )
        # Check budget as analytic
        self.budget_period.control_budget = True
        self.budget_period.control_level = "analytic"

        purchase_request = purchase_request.with_context(
            force_date_commit=purchase_request.date_start
        )
        self.assertEqual(self.budget_control.amount_balance, 300)
        purchase_request.button_to_approve()
        purchase_request.button_approved()
        self.assertEqual(self.budget_control.amount_purchase_request, 30)
        self.assertEqual(self.budget_control.amount_purchase, 0)
        self.assertEqual(self.budget_control.amount_balance, 270)
        # Check create TE from PR with no carry forward budget
        wiz = self.pr_te_wiz.with_context(
            active_model="purchase.request", active_ids=[purchase_request.id]
        ).create({})
        self.assertEqual(len(wiz.item_ids), 1)
        wiz.make_purchase_requisition()
        # Check PR link to TE must have 1
        self.assertEqual(purchase_request.requisition_count, 1)
        action = purchase_request.action_view_purchase_requisition()
        requisition = purchase_request.line_ids.requisition_lines.requisition_id
        self.assertEqual(action["res_id"], requisition.id)
        # No forward budget, analytic account (TE Line) = analytic account (PR Line)
        self.assertEqual(
            purchase_request.line_ids.analytic_account_id,
            requisition.line_ids.account_analytic_id,
        )
        # # Delete TE for test new TE with forward analytic
        # requisition.unlink()
        forward_budget_commit = self.BudgetCommit.create(
            {
                "name": "Test Forward Commit",
                "to_budget_period_id": self.next_budget_period.id,
                "purchase_request": True,
            }
        )
        forward_budget_commit.action_review_budget_commit()
        self.assertEqual(len(forward_budget_commit.forward_purchase_request_ids), 1)
        wizard_preview = forward_budget_commit.preview_budget_commit_forward_info()
        forward_info = (
            self.env["budget.commit.forward.info"]
            .with_context(
                default_forward_id=wizard_preview["context"]["default_forward_id"],
                default_forward_info_line_ids=wizard_preview["context"][
                    "default_forward_info_line_ids"
                ],
            )
            .create({})
        )
        # After forward budget commit, PR has forward analytic
        self.assertFalse(purchase_request.line_ids.fwd_analytic_account_id)
        forward_info.action_budget_commit_forward()
        self.assertTrue(purchase_request.line_ids.fwd_analytic_account_id)
        # Check create TE from PR with carry forward budget
        wiz = self.pr_te_wiz.with_context(
            active_model="purchase.request", active_ids=[purchase_request.id]
        ).create({})
        self.assertEqual(len(wiz.item_ids), 1)
        wiz.make_purchase_requisition()
        # Analytic account (TE Line) = Forward analytic account (PR Line)
        self.assertEqual(
            purchase_request.line_ids.fwd_analytic_account_id,
            requisition.line_ids.account_analytic_id,
        )
