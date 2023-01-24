# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

from freezegun import freeze_time

from odoo.tests import tagged
from odoo.tests.common import Form

from odoo.addons.budget_activity.tests.test_budget_activity import TestBudgetActivity


@tagged("post_install", "-at_install")
class TestBudgetActivityContract(TestBudgetActivity):
    @classmethod
    @freeze_time("2001-02-01")
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
            ct.commit_budget = True
            for ct_line in ct_lines:
                with ct.contract_line_ids.new() as line:
                    line.product_id = ct_line["product_id"]
                    line.name = ct_line["name"]
                    line.quantity = ct_line["quantity"]
                    line.price_unit = ct_line["price_unit"]
                    line.analytic_account_id = ct_line["analytic_id"]
                    line.activity_id = ct_line["activity_id"]
        contract = ct.save()
        return contract

    @freeze_time("2001-02-01")
    def test_01_budget_activity_contract(self):
        """
        On contract,
        - If no activity, budget follows product's account
        - If activity is selected, account follows activity's regardless of product
        """
        # Control budget
        self.budget_period.control_budget = True
        self.budget_control.action_done()

        # Prepare CT
        contract = self._create_contract(
            [
                {
                    "product_id": self.product2,  # KPI2 = 30
                    "name": self.product2.name,
                    "quantity": 3,
                    "price_unit": 10,
                    "analytic_id": self.costcenter1,
                    "activity_id": self.activity3,
                },
            ]
        )
        contract = contract.with_context(force_date_commit=contract.date_start)
        contract.recompute_budget_move()  # No budget check no error
        # PO Commit = 30, INV Actual = 0, Balance = 2370
        self.assertEqual(self.budget_control.amount_commit, 30)
        self.assertEqual(self.budget_control.amount_actual, 0)
        self.assertEqual(self.budget_control.amount_balance, 2370)
        self.assertEqual(
            contract.budget_move_ids.account_id,
            contract.contract_line_ids.activity_id.account_id,
        )
        # Create and post invoice
        contract.recurring_create_invoice()
        self.assertEqual(contract.invoice_count, 1)
        invoice = contract._get_related_invoices()[:1]
        # Change qty to 1, will not make invoice return by qty like PO <-> INV
        # It will always return the full line amount in the same way PR <-> PO
        invoice.with_context(check_move_validity=False).invoice_line_ids[0].quantity = 1
        invoice.with_context(check_move_validity=False)._onchange_invoice_line_ids()
        invoice.action_post()
        # CT Commit = 20, INV Actual = 10, Balance = 2370
        self.budget_control.invalidate_cache()
        self.assertEqual(self.budget_control.amount_commit, 20)
        self.assertEqual(self.budget_control.amount_actual, 10)
        self.assertEqual(self.budget_control.amount_balance, 2370)
        # # Cancel invoice
        invoice.button_cancel()
        self.budget_control.invalidate_cache()
        self.assertEqual(self.budget_control.amount_commit, 30)
        self.assertEqual(self.budget_control.amount_actual, 0)
        self.assertEqual(self.budget_control.amount_balance, 2370)
