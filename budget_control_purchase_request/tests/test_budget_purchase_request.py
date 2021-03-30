# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

from freezegun import freeze_time

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import Form

from odoo.addons.budget_control.tests.common import BudgetControlCommon


@tagged("post_install", "-at_install")
class TestBudgetControl(BudgetControlCommon):
    @classmethod
    @freeze_time("2001-02-01")
    def setUpClass(cls):
        super().setUpClass()
        # Create sample ready to use Budget Control
        cls.budget_control = cls.BudgetControl.create(
            {
                "name": "CostCenter1/%s" % cls.year,
                "budget_id": cls.budget_period.mis_budget_id.id,
                "analytic_account_id": cls.costcenter1.id,
                "plan_date_range_type_id": cls.date_range_type.id,
            }
        )
        # Test item created for 3 kpi x 4 quarters = 12 budget items
        assert len(cls.budget_control.item_ids) == 12
        # Assign budget.control amount: KPI1 = 100, KPI2=800, Total=300
        cls.budget_control.item_ids.filtered(
            lambda x: x.kpi_expression_id == cls.kpi1.expression_ids[0]
        )[:1].write({"amount": 100})
        cls.budget_control.item_ids.filtered(
            lambda x: x.kpi_expression_id == cls.kpi2.expression_ids[0]
        )[:1].write({"amount": 200})
        cls.budget_control.allocated_amount = 300
        cls.budget_control.action_done()

    @freeze_time("2001-02-01")
    def _create_purchase_request(self, pr_lines):
        PurchaseRequest = self.env["purchase.request"]
        view_id = "purchase_request.view_purchase_request_form"
        ctx = {}
        with Form(PurchaseRequest.with_context(ctx), view=view_id) as pr:
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
    def test_01_budget_purchase_request(self):
        """
        On Purchase Order
        (1) Test case, no budget check -> OK
        (2) Check Budget with analytic_kpi -> Error amount exceed on kpi1
        (3) Check Budget with analytic -> OK
        (2) Check Budget with analytic -> Error amount exceed
        """
        # KPI1 = 100, KPI2 = 200, Total = 300
        self.assertEqual(300, self.budget_control.amount_budget)
        # Prepare PR
        purchase_request = self._create_purchase_request(
            [
                {
                    "product_id": self.product1,  # KPI1 = 101 -> error
                    "product_qty": 1,
                    "estimated_cost": 101,
                    "analytic_id": self.costcenter1,
                },
                {
                    "product_id": self.product2,  # KPI2 = 198
                    "product_qty": 2,
                    "estimated_cost": 198,  # This is the price of qty 2
                    "analytic_id": self.costcenter1,
                },
            ]
        )
        # (1) No budget check first
        self.budget_period.purchase_request = False
        self.budget_period.control_level = "analytic_kpi"
        # force date commit, as freeze_time not work for write_date
        purchase_request = purchase_request.with_context(
            force_date_commit=purchase_request.date_start
        )
        self.assertEqual(self.budget_control.amount_balance, 300)
        purchase_request.button_to_approve()
        purchase_request.button_approved()  # No budget check no error
        # (2) Check Budget with analytic_kpi -> Error
        purchase_request.button_draft()
        self.assertEqual(self.budget_control.amount_balance, 300)
        self.budget_period.purchase_request = True  # Set to check budget
        # kpi 1 (kpi1) & CostCenter1, will result in $ -1.00
        with self.assertRaises(UserError):
            purchase_request.button_to_approve()
        purchase_request.button_draft()
        # (3) Check Budget with analytic -> OK
        self.budget_period.control_level = "analytic"
        purchase_request.button_to_approve()
        purchase_request.button_approved()
        self.assertEqual(self.budget_control.amount_balance, 1)
        purchase_request.button_draft()
        self.assertEqual(self.budget_control.amount_balance, 300)
        # (4) Amount exceed -> Error
        purchase_request.line_ids.write({"estimated_cost": 150.5})  # Total 301
        # CostCenter1, will result in $ -1.00
        with self.assertRaises(UserError):
            purchase_request.button_to_approve()

    # @freeze_time("2001-02-01")
    # def test_02_budget_purchase_to_invoice(self):
    #     """
    #     On Purchase Order
    #     (1) Test case, no budget check -> OK
    #     (2) Check Budget with analytic_kpi -> Error amount exceed on kpi1
    #     (3) Check Budget with analytic -> OK
    #     (4) Check Budget with analytic -> Error amount exceed
    #     """
    #     # KPI1 = 100, KPI2 = 200, Total = 300
    #     self.assertEqual(300, self.budget_control.amount_budget)
    #     # Prepare PO on kpi1 with qty 3 and unit_price 10
    #     purchase = self._create_purchase(
    #         [
    #             {
    #                 "product_id": self.product1,  # KPI1 = 30
    #                 "product_qty": 3,
    #                 "price_unit": 10,
    #                 "analytic_id": self.costcenter1,
    #             },
    #         ]
    #     )
    #     self.budget_period.purchase = True
    #     self.budget_period.control_level = "analytic"
    #     purchase = purchase.with_context(force_date_commit=purchase.date_order)
    #     purchase.button_confirm()
    #     # PO Commit = 30, INV Actual = 0, Balance = 270
    #     self.assertEqual(self.budget_control.amount_commit, 30)
    #     self.assertEqual(self.budget_control.amount_actual, 0)
    #     self.assertEqual(self.budget_control.amount_balance, 270)
    #     # Create and post invoice
    #     purchase.action_create_invoice()
    #     self.assertEqual(purchase.invoice_status, "invoiced")
    #     invoice = purchase.invoice_ids[:1]
    #     # Change qty to 1
    #     invoice.with_context(check_move_validity=False).invoice_line_ids[
    #         0
    #     ].quantity = 1
    #     invoice.with_context(
    #         check_move_validity=False
    #     )._onchange_invoice_line_ids()
    #     invoice.action_post()
    #     # PO Commit = 20, INV Actual = 10, Balance = 270
    #     self.budget_control.invalidate_cache()
    #     self.assertEqual(self.budget_control.amount_commit, 20)
    #     self.assertEqual(self.budget_control.amount_actual, 10)
    #     self.assertEqual(self.budget_control.amount_balance, 270)
    #     # # Cancel invoice
    #     invoice.button_cancel()
    #     self.budget_control.invalidate_cache()
    #     self.assertEqual(self.budget_control.amount_commit, 30)
    #     self.assertEqual(self.budget_control.amount_actual, 0)
    #     self.assertEqual(self.budget_control.amount_balance, 270)
