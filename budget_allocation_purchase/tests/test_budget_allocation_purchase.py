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
class TestBudgetAllocationPurchase(TestBudgetAllocation):
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
                    line.account_analytic_id = po_line["analytic_id"]
        purchase = po.save()
        return purchase

    @freeze_time("2001-02-01")
    def test_01_commitment_expense_fund(self):
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
        purchase = self._create_purchase(
            [
                {
                    "product_id": self.product1,
                    "product_qty": 1,
                    "price_unit": 30,
                    "analytic_id": self.costcenter1,
                },
            ]
        )
        # force date commit, as freeze_time not work for write_date
        purchase = purchase.with_context(force_date_commit=purchase.date_order)
        with self.assertRaises(UserError):
            purchase.button_confirm()
        # Add fund1, tags1 in expense line
        purchase.order_line.fund_id = self.fund1_g1.id
        purchase.order_line.analytic_tag_ids = [(4, self.analytic_tag1.id)]
        purchase.button_confirm()
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
