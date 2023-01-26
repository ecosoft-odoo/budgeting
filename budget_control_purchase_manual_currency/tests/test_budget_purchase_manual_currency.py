# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

from freezegun import freeze_time

from odoo.tests import tagged
from odoo.tests.common import Form

from odoo.addons.budget_control.tests.common import BudgetControlCommon


@tagged("post_install", "-at_install")
class TestBudgetControlPurchaseManualCurrency(BudgetControlCommon):
    @classmethod
    @freeze_time("2001-02-01")
    def setUpClass(cls):
        super().setUpClass()
        cls.currency_eur = cls.env.ref("base.EUR")
        cls.currency_eur.active = True  # active multi currency
        cls.currency_eur.write(
            {
                "rate_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "2001-02-01",
                            "company_rate": 0.5,
                        },
                    )
                ]
            }
        )
        cls.currency_usd = cls.env.ref("base.USD")
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
        # Assign budget.control amount: KPI1=1000, KPI2=2000, Total=3000
        cls.budget_control.line_ids.filtered(lambda x: x.kpi_id == cls.kpi1)[:1].write(
            {"amount": 1000}
        )
        cls.budget_control.line_ids.filtered(lambda x: x.kpi_id == cls.kpi2)[:1].write(
            {"amount": 2000}
        )
        cls.budget_control.flush()  # Need to flush data into table, so it can be sql
        cls.budget_control.allocated_amount = 3000
        cls.budget_control.action_done()
        # Purchase method
        cls.product1.product_tmpl_id.purchase_method = "purchase"

    @freeze_time("2001-02-01")
    def _create_purchase(self, po_lines):
        Purchase = self.env["purchase.order"]
        view_id = "purchase.purchase_order_form"
        with Form(Purchase, view=view_id) as po:
            po.partner_id = self.vendor
            po.date_order = datetime.today()
            po.currency_id = self.currency_eur  # multi currency
            for po_line in po_lines:
                with po.order_line.new() as line:
                    line.product_id = po_line["product_id"]
                    line.product_qty = po_line["product_qty"]
                    line.price_unit = po_line["price_unit"]
                    line.account_analytic_id = po_line["analytic_id"]
        purchase = po.save()
        return purchase

    @freeze_time("2001-02-01")
    def test_01_budget_purchase_currency(self):
        self.budget_period.control_budget = True  # Set to check budget
        self.assertEqual(self.budget_control.amount_budget, 3000)
        self.assertEqual(self.budget_control.amount_balance, 3000)
        # Prepare PO
        purchase = self._create_purchase(
            [
                {
                    "product_id": self.product1,
                    "product_qty": 1,
                    "price_unit": 100,
                    "analytic_id": self.costcenter1,
                },
            ]
        )
        # force date commit, as freeze_time not work for write_date
        purchase = purchase.with_context(force_date_commit=purchase.date_order)
        purchase.button_confirm()
        self.assertEqual(purchase.budget_move_ids.debit, 130.81)
        purchase.button_draft()
        # Change custom rate to 10
        with Form(purchase) as p:
            p.manual_currency = True
            p.custom_rate = 10.0
        self.assertEqual(purchase.custom_rate, 10.0)
        purchase.button_confirm()
        # Check budget should convert with custom rate
        self.assertEqual(purchase.budget_move_ids.debit, 10.0)
        self.assertEqual(purchase.budget_move_ids.amount_currency, 100.0)
        self.assertEqual(self.budget_control.amount_commit, 10)
        self.assertEqual(self.budget_control.amount_balance, 2990)
