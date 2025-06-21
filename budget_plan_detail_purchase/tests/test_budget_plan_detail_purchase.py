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
class TestBudgetPlanDetailPurchase(TestBudgetPlanDetail):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Purchase method
        cls.product1.product_tmpl_id.purchase_method = "purchase"

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
                    if po_line.get("fund_id"):
                        line.fund_id = po_line["fund_id"]
                    if po_line.get("analytic_tag_ids"):
                        line.analytic_tag_ids = po_line["analytic_tag_ids"]
        purchase = po.save()
        return purchase

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
        purchase = self._create_purchase(
            [
                {
                    "product_id": self.product1,  # KPI1 = 601 -> error
                    "product_qty": 1,
                    "price_unit": 601,
                    "analytic_distribution": analytic_distribution,
                },
            ]
        )
        # force date commit, as freeze_time not work for write_date
        purchase = purchase.with_context(force_date_commit=purchase.date_order)
        with self.assertRaisesRegex(
            UserError, "is not allocated on budget plan detail"
        ):
            purchase.button_confirm()
        purchase.button_cancel()
        purchase.button_draft()

        # Add fund1, tags1 in purchase line
        purchase.order_line.fund_id = self.fund1_g1.id
        purchase.order_line.analytic_tag_ids = [(4, self.analytic_tag1.id)]

        # Purchase commit amount 601 > allocated amount 600.0, it should error
        with self.assertRaisesRegex(
            UserError, "spend amount over budget plan detail limit"
        ):
            purchase.button_confirm()
        purchase.button_cancel()
        purchase.button_draft()

        purchase.order_line.price_unit = 400.0
        purchase.button_confirm()

        self.assertEqual(purchase.budget_move_ids.fund_id, self.fund1_g1)
        self.assertEqual(purchase.budget_move_ids.analytic_tag_ids, self.analytic_tag1)
        self.assertAlmostEqual(budget_control.amount_purchase, 400.0)

        # Create and post invoice
        purchase.action_create_invoice()
        self.assertEqual(purchase.invoice_status, "invoiced")
        invoice = purchase.invoice_ids[:1]
        invoice.invoice_date = invoice.date
        self.assertEqual(invoice.invoice_line_ids.fund_id, self.fund1_g1)
        self.assertEqual(invoice.invoice_line_ids.analytic_tag_ids, self.analytic_tag1)
        invoice.action_post()
        self.assertEqual(invoice.budget_move_ids.fund_id, self.fund1_g1)
        self.assertEqual(invoice.budget_move_ids.analytic_tag_ids, self.analytic_tag1)
