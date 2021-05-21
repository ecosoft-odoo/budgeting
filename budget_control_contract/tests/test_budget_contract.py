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
                "kpi_ids": [cls.kpi1.id, cls.kpi2.id, cls.kpi3.id],
            }
        )
        # Test item created for 3 kpi x 4 quarters = 12 budget items
        cls.budget_control.prepare_budget_control_matrix()
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
    def _create_contract(self, ct_lines):
        Contract = self.env["contract.contract"]
        view_id = "contract.contract_contract_supplier_form_view"
        ctx = {"is_contract": 1, "default_contract_type": "purchase"}
        with Form(Contract.with_context(ctx), view=view_id) as ct:
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
        contract = ct.save()
        return contract

    @freeze_time("2001-02-01")
    def test_01_budget_contract(self):
        """
        On Contract Order
        (1) Test case, no budget check -> OK
        (2) Check Budget with analytic_kpi -> Error amount exceed on kpi1
        (3) Check Budget with analytic -> OK
        (2) Check Budget with analytic -> Error amount exceed
        """
        # KPI1 = 100, KPI2 = 200, Total = 300
        self.assertEqual(300, self.budget_control.amount_budget)
        # Prepare CT
        contract = self._create_contract(
            [
                {
                    "product_id": self.product1,  # KPI1 = 101 -> error
                    "name": self.product1.name,
                    "quantity": 1,
                    "price_unit": 101,
                    "analytic_id": self.costcenter1,
                },
                {
                    "product_id": self.product2,  # KPI2 = 198
                    "name": self.product2.name,
                    "quantity": 2,
                    "price_unit": 99,
                    "analytic_id": self.costcenter1,
                },
            ]
        )

        # (1) No budget check first
        self.budget_period.contract = False
        self.budget_period.control_level = "analytic_kpi"
        # force date commit, as freeze_time not work for write_date
        contract = contract.with_context(force_date_commit=contract.date_start)
        contract.recompute_budget_move()  # No budget check no error
        # (2) Check Budget with analytic_kpi -> Error
        self.budget_period.contract = True  # Set to check budget
        # kpi 1 (kpi1) & CostCenter1, will result in $ -1.00
        with self.assertRaises(UserError):
            contract.recompute_budget_move()
        # (3) Check Budget with analytic -> OK
        self.budget_period.control_level = "analytic"
        contract.recompute_budget_move()
        self.assertEqual(self.budget_control.amount_balance, 1)
        contract.close_budget_move()
        contract.invalidate_cache()
        self.assertEqual(self.budget_control.amount_balance, 300)
        # (4) Amount exceed -> Error
        contract.contract_line_ids[1].price_unit = 100
        # CostCenter1, will result in $ -1.00
        with self.assertRaises(UserError):
            contract.recompute_budget_move()

    @freeze_time("2001-02-01")
    def test_02_budget_contract_to_invoice(self):
        """ Contract to Invoice, commit and uncommit """
        # KPI1 = 100, KPI2 = 200, Total = 300
        self.assertEqual(300, self.budget_control.amount_budget)
        # Prepare CT on kpi1 with qty 3 and unit_price 10
        contract = self._create_contract(
            [
                {
                    "product_id": self.product1,  # KPI1 = 30
                    "name": self.product1.name,
                    "quantity": 3,
                    "price_unit": 10,
                    "analytic_id": self.costcenter1,
                },
            ]
        )
        self.budget_period.contract = True
        self.budget_period.control_level = "analytic"
        contract = contract.with_context(force_date_commit=contract.date_start)
        contract.recompute_budget_move()
        # CT Commit = 30, INV Actual = 0, Balance = 270
        self.assertEqual(self.budget_control.amount_commit, 30)
        self.assertEqual(self.budget_control.amount_actual, 0)
        self.assertEqual(self.budget_control.amount_balance, 270)
        # Create and post invoice
        contract.recurring_create_invoice()
        self.assertEqual(contract.invoice_count, 1)
        invoice = contract._get_related_invoices()[:1]
        # Change qty to 1, will not make invoice return by qty like PO <-> INV
        # It will always return the full line amount in the same way PR <-> PO
        invoice.with_context(check_move_validity=False).invoice_line_ids[
            0
        ].quantity = 1
        invoice.with_context(
            check_move_validity=False
        )._onchange_invoice_line_ids()
        invoice.action_post()
        # CT Commit = 0, INV Actual = 10, Balance = 290
        self.budget_control.invalidate_cache()
        self.assertEqual(self.budget_control.amount_commit, 0)
        self.assertEqual(self.budget_control.amount_actual, 10)
        self.assertEqual(self.budget_control.amount_balance, 290)
        # # Cancel invoice
        invoice.button_cancel()
        self.budget_control.invalidate_cache()
        self.assertEqual(self.budget_control.amount_commit, 30)
        self.assertEqual(self.budget_control.amount_actual, 0)
        self.assertEqual(self.budget_control.amount_balance, 270)

    @freeze_time("2001-02-01")
    def test_03_budget_recompute_and_close_budget_move(self):
        """Contract to Invoice (partial)
        - Test recompute on both Contract and Invoice
        - Test close on both Contract and Invoice"""
        # Prepare PO on kpi1 with qty 3 and unit_price 10
        contract = self._create_contract(
            [
                {
                    "product_id": self.product1,  # KPI1 = 101 -> error
                    "name": self.product1.name,
                    "quantity": 2,
                    "price_unit": 15,
                    "analytic_id": self.costcenter1,
                },
                {
                    "product_id": self.product2,  # KPI1 = 101 -> error
                    "name": self.product2.name,
                    "quantity": 4,
                    "price_unit": 10,
                    "analytic_id": self.costcenter1,
                },
            ]
        )
        self.budget_period.contract = True
        self.budget_period.control_level = "analytic"
        contract = contract.with_context(force_date_commit=contract.date_start)
        contract.recompute_budget_move()
        # CT Commit = 70, INV Actual = 0
        self.assertEqual(self.budget_control.amount_contract, 70)
        self.assertEqual(self.budget_control.amount_actual, 0)
        # Create and post invoice
        contract.recurring_create_invoice()
        self.assertEqual(contract.invoice_count, 1)
        invoice = contract._get_related_invoices()[:1]
        # Change qty to 1 and 3 (it still return in full)
        invoice = invoice.with_context(check_move_validity=False)
        invoice.invoice_line_ids[0].quantity = 1
        invoice.invoice_line_ids[1].quantity = 3
        invoice._onchange_invoice_line_ids()
        invoice.action_post()
        # CT Commit = 25, INV Actual = 45
        self.budget_control.invalidate_cache()
        self.assertEqual(self.budget_control.amount_contract, 0)
        self.assertEqual(self.budget_control.amount_actual, 45)
        # Test recompute, must be same
        contract.recompute_budget_move()
        self.budget_control.invalidate_cache()
        self.assertEqual(self.budget_control.amount_contract, 0)
        self.assertEqual(self.budget_control.amount_actual, 45)
        invoice.recompute_budget_move()
        self.budget_control.invalidate_cache()
        self.assertEqual(self.budget_control.amount_actual, 45)
        self.assertEqual(self.budget_control.amount_contract, 0)
        # Test close budget move
        contract.close_budget_move()
        self.budget_control.invalidate_cache()
        self.assertEqual(self.budget_control.amount_contract, 0)
        self.assertEqual(self.budget_control.amount_actual, 45)
        # Test close budget move
        invoice.close_budget_move()
        self.budget_control.invalidate_cache()
        self.assertEqual(self.budget_control.amount_contract, 0)
        self.assertEqual(self.budget_control.amount_actual, 0)
