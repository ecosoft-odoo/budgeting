# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

from freezegun import freeze_time

from odoo.tests import tagged
from odoo.tests.common import Form

from odoo.addons.budget_allocation.tests.test_budget_allocation import (
    TestBudgetAllocation,
)


@tagged("post_install", "-at_install")
class TestBudgetAllocationExpense(TestBudgetAllocation):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    @freeze_time("2001-02-01")
    def _create_contract(self, ct_lines):
        Contract = self.env["contract.contract"]
        view_id = "contract.contract_contract_supplier_form_view"
        with Form(
            Contract.with_context(is_contract=1, default_contract_type="purchase"),
            view=view_id,
        ) as ct:
            ct.name = "/"
            ct.partner_id = self.vendor
            ct.date_start = datetime.today()
            for ct_line in ct_lines:
                with ct.contract_line_ids.new() as line:
                    line.product_id = ct_line["product_id"]
                    line.name = ct_line["name"]
                    line.quantity = ct_line["quantity"]
                    line.price_unit = ct_line["price_unit"]
                    line.analytic_account_id = ct_line["analytic_id"]
        contract = ct.save()
        return contract

    @freeze_time("2001-02-01")
    def test_01_commitment_contract_fund(self):
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
        # Commit expense without allocation (no fund, no tags)
        contract = self._create_contract(
            [
                {
                    "product_id": self.product1,  # KPI2 = 30
                    "name": self.product1.name,
                    "quantity": 3,
                    "price_unit": 10,
                    "analytic_id": self.costcenter1,
                },
            ]
        )
        contract = contract.with_context(force_date_commit=contract.date_start)
        # Add fund1, tags1 in contract line
        contract.contract_line_ids.fund_id = self.fund1_g1.id
        contract.contract_line_ids.analytic_tag_ids = [(4, self.analytic_tag1.id)]
        # Commit budget in contract
        contract.commit_budget = True
        # Costcenter1 = 250, CT Commit = 30, INV Actual = 0, Balance = 220
        self.assertEqual(budget_control.amount_commit, 30)
        self.assertEqual(budget_control.amount_actual, 0)
        self.assertEqual(budget_control.amount_balance, 220)
        self.assertEqual(
            contract.budget_move_ids.fund_id, contract.contract_line_ids.fund_id
        )
        # Create and post invoice
        contract.recurring_create_invoice()
        self.assertEqual(contract.invoice_count, 1)
        invoice = contract._get_related_invoices()[:1]
        # Change qty to 1, will not make invoice return by qty like Contract <-> INV
        invoice.with_context(check_move_validity=False).invoice_line_ids[0].quantity = 1
        invoice.with_context(check_move_validity=False)._onchange_invoice_line_ids()
        invoice.action_post()
        # CT Commit = 20, INV Actual = 10, Balance = 220
        budget_control.invalidate_cache()
        self.assertEqual(budget_control.amount_commit, 20)
        self.assertEqual(budget_control.amount_actual, 10)
        self.assertEqual(budget_control.amount_balance, 220)
        self.assertEqual(
            invoice.invoice_line_ids.fund_id, contract.contract_line_ids.fund_id
        )
        self.assertEqual(
            invoice.invoice_line_ids.analytic_tag_ids,
            contract.contract_line_ids.analytic_tag_ids,
        )
        # Cancel invoice
        invoice.button_cancel()
        budget_control.invalidate_cache()
        self.assertEqual(budget_control.amount_commit, 30)
        self.assertEqual(budget_control.amount_actual, 0)
        self.assertEqual(budget_control.amount_balance, 220)
