# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

from dateutil.rrule import MONTHLY

from odoo import Command
from odoo.tests.common import TransactionCase


class BudgetControlCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.budget_include_tax = False  # Not Tax Included
        cls.year = datetime.now().year
        cls.RangeType = cls.env["date.range.type"]
        cls.Analytic = cls.env["account.analytic.account"]
        cls.AnalyticPlan = cls.env["account.analytic.plan"]
        cls.Account = cls.env["account.account"]
        cls.BudgetControl = cls.env["budget.control"]
        cls.BudgetTemplate = cls.env["budget.template"]
        cls.BudgetKPI = cls.env["budget.kpi"]
        cls.Product = cls.env["product.product"]
        cls.Partner = cls.env["res.partner"]
        cls.Move = cls.env["account.move"]
        cls.BudgetAdjust = cls.env["budget.move.adjustment"]
        cls.CommitForward = cls.env["budget.commit.forward"]

        # Create vendor
        cls.vendor = cls.Partner.create({"name": "Sample Vendor"})
        # Create quarterly date range for current year
        cls.date_range_type = cls.RangeType.create({"name": "TestQuarter"})
        cls._create_date_range_quarter(cls)
        # Setup some required entity
        cls.account_kpi1 = cls.Account.create(
            {"name": "KPI1", "code": "KPI1", "account_type": "expense"}
        )
        cls.account_kpi2 = cls.Account.create(
            {"name": "KPI2", "code": "KPI2", "account_type": "expense"}
        )
        cls.account_kpi3 = cls.Account.create(
            {"name": "KPI3", "code": "KPI3", "account_type": "expense"}
        )
        # Create an extra account, but not in control
        cls.account_kpiX = cls.Account.create(
            {"name": "KPIX", "code": "KPIX", "account_type": "expense"}
        )
        # Create an extra account, for advance
        cls.account_kpiAV = cls.Account.create(
            {
                "name": "KPIAV",
                "code": "KPIAV",
                "account_type": "asset_current",
                "reconcile": True,
            }
        )
        cls.kpi1 = cls.BudgetKPI.create({"name": "kpi 1"})
        cls.kpi2 = cls.BudgetKPI.create({"name": "kpi 2"})
        cls.kpi3 = cls.BudgetKPI.create({"name": "kpi 3"})

        cls.product1 = cls.Product.create(
            {
                "name": "Product 1",
                "property_account_expense_id": cls.account_kpi1.id,
            }
        )
        cls.product2 = cls.Product.create(
            {
                "name": "Product 2",
                "property_account_expense_id": cls.account_kpi2.id,
            }
        )
        cls.template = cls.BudgetTemplate.create({"name": "Test KPI"})

        # Create budget kpis
        cls._create_budget_template_kpi(cls)
        # Create budget.period for current year
        cls.budget_period = cls._create_budget_period_fy(
            cls, cls.template.id, cls.date_range_type.id
        )

        cls.aa_plan1 = cls.AnalyticPlan.create({"name": "Plan1"})
        # Create budget.control for CostCenter1,
        # by selected budget_id and date range (by quarter)
        cls.costcenter1 = cls.Analytic.create(
            {"name": "CostCenter1", "plan_id": cls.aa_plan1.id}
        )
        cls.costcenterX = cls.Analytic.create(
            {"name": "CostCenterX", "plan_id": cls.aa_plan1.id}
        )

    def _create_date_range_quarter(self):
        Generator = self.env["date.range.generator"]
        generator = Generator.create(
            {
                "date_start": "%s-01-01" % self.year,
                "name_prefix": "%s/Test/Q-" % self.year,
                "type_id": self.date_range_type.id,
                "duration_count": 3,
                "unit_of_time": str(MONTHLY),
                "count": 4,
            }
        )
        generator.action_apply()

    def _create_budget_template_kpi(self):
        # create template kpis
        self.template_line1 = self.env["budget.template.line"].create(
            {
                "template_id": self.template.id,
                "kpi_id": self.kpi1.id,
                "account_ids": [(4, self.account_kpi1.id)],
            }
        )
        self.template_line2 = self.env["budget.template.line"].create(
            {
                "template_id": self.template.id,
                "kpi_id": self.kpi2.id,
                "account_ids": [(4, self.account_kpi2.id)],
            }
        )
        self.template_line3 = self.env["budget.template.line"].create(
            {
                "template_id": self.template.id,
                "kpi_id": self.kpi3.id,
                "account_ids": [(4, self.account_kpi3.id)],
            }
        )

    def _create_budget_period_fy(self, template_id, date_range_type_id):
        BudgetPeriod = self.env["budget.period"]
        budget_period = BudgetPeriod.create(
            {
                "name": "Budget for FY%s" % self.year,
                "template_id": template_id,
                "bm_date_from": "%s-01-01" % self.year,
                "bm_date_to": "%s-12-31" % self.year,
                "plan_date_range_type_id": date_range_type_id,
                "control_level": "analytic_kpi",
            }
        )
        return budget_period

    def _create_invoice(
        self, inv_type, vendor, invoice_date, analytic_distribution, invoice_lines
    ):
        invoice = self.Move.create(
            {
                "move_type": inv_type,
                "partner_id": vendor.id,
                "invoice_date": invoice_date,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "quantity": 1,
                            "account_id": il.get("account"),
                            "price_unit": il.get("price_unit"),
                            "analytic_distribution": analytic_distribution,
                        },
                    )
                    for il in invoice_lines
                ],
            }
        )
        return invoice

    def _create_simple_bill(self, analytic_distribution, account, amount):
        invoice = self.Move.create(
            {
                "move_type": "in_invoice",
                "partner_id": self.vendor.id,
                "invoice_date": datetime.today(),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "quantity": 1,
                            "account_id": account.id,
                            "price_unit": amount,
                            "analytic_distribution": analytic_distribution,
                        },
                    )
                ],
            }
        )
        return invoice
