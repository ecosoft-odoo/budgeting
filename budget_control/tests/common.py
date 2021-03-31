# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import datetime

from dateutil.rrule import MONTHLY

from odoo.tests.common import Form, SavepointCase


class BudgetControlCommon(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.year = datetime.now().year
        RangeType = cls.env["date.range.type"]
        cls.Analytic = cls.env["account.analytic.account"]
        cls.BudgetControl = cls.env["budget.control"]
        Partner = cls.env["res.partner"]
        # Vendor
        cls.vendor = Partner.create({"name": "Sample Vendor"})
        # Create quarterly date range for current year
        cls.date_range_type = RangeType.create({"name": "TestQuarter"})
        cls._create_date_range_quarter(cls)
        # Setup some required entity
        Account = cls.env["account.account"]
        type_exp = cls.env.ref("account.data_account_type_expenses").id
        cls.account_kpi1 = Account.create(
            {"name": "KPI1", "code": "KPI1", "user_type_id": type_exp}
        )
        cls.account_kpi2 = Account.create(
            {"name": "KPI2", "code": "KPI2", "user_type_id": type_exp}
        )
        cls.account_kpi3 = Account.create(
            {"name": "KPI3", "code": "KPI3", "user_type_id": type_exp}
        )
        # Create an extra account, but not in control
        cls.account_kpiX = Account.create(
            {"name": "KPIX", "code": "KPIX", "user_type_id": type_exp}
        )
        Product = cls.env["product.product"]
        cls.product1 = Product.create(
            {
                "name": "Product 1",
                "property_account_expense_id": cls.account_kpi1.id,
            }
        )
        cls.product2 = Product.create(
            {
                "name": "Product 2",
                "property_account_expense_id": cls.account_kpi2.id,
            }
        )
        # Create budget kpis
        cls.report = cls._create_mis_report_kpi(cls)
        # Create budget.period for current year
        cls.budget_period = cls._create_budget_period_fy(
            cls, cls.report.id, cls.date_range_type.id
        )
        # Create budget.control for CostCenter1,
        #  by selected budget_id and date range (by quarter)
        cls.costcenter1 = cls.Analytic.create({"name": "CostCenter1"})
        cls.costcenterX = cls.Analytic.create({"name": "CostCenterX"})

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

    def _create_mis_report_kpi(self):
        # create report
        report = self.env["mis.report"].create(
            dict(
                name="Test KPI",
            )
        )
        self.kpi1 = self.env["mis.report.kpi"].create(
            dict(
                report_id=report.id,
                name="kpi1",
                budgetable=True,
                description="kpi 1",
                expression="balp[KPI1]",
            )
        )
        self.kpi2 = self.env["mis.report.kpi"].create(
            dict(
                report_id=report.id,
                name="kpi2",
                budgetable=True,
                description="kpi 2",
                expression="balp[KPI2]",
            )
        )
        self.kpi3 = self.env["mis.report.kpi"].create(
            dict(
                report_id=report.id,
                name="kpi3",
                budgetable=True,
                description="kpi 3",
                expression="balp[KPI3]",
            )
        )
        return report

    def _create_budget_period_fy(self, report_id, date_range_type_id):
        BudgetPeriod = self.env["budget.period"]
        budget_period = BudgetPeriod.create(
            {
                "name": "Budget for FY%s" % self.year,
                "report_id": report_id,
                "bm_date_from": "%s-01-01" % self.year,
                "bm_date_to": "%s-12-31" % self.year,
                "plan_date_range_type_id": date_range_type_id,
                "control_level": "analytic_kpi",
            }
        )
        return budget_period

    def _create_invoice(
        self, inv_type, vendor, invoice_date, analytic, invoice_lines
    ):
        Invoice = self.env["account.move"]
        with Form(
            Invoice.with_context(default_move_type=inv_type),
            view="account.view_move_form",
        ) as inv:
            inv.partner_id = vendor
            inv.invoice_date = invoice_date
            for il in invoice_lines:
                with inv.invoice_line_ids.new() as line:
                    line.quantity = 1
                    line.account_id = il.get("account")
                    line.price_unit = il.get("price_unit")
                    line.analytic_account_id = analytic
        invoice = inv.save()
        return invoice

    def _create_simple_bill(self, analytic, account, amount):
        Invoice = self.env["account.move"]
        ctx = {"default_move_type": "in_invoice"}
        view_id = "account.view_move_form"
        with Form(Invoice.with_context(ctx), view=view_id) as inv:
            inv.partner_id = self.vendor
            inv.invoice_date = datetime.today()
            with inv.invoice_line_ids.new() as line:
                line.quantity = 1
                line.account_id = account
                line.price_unit = amount
                line.analytic_account_id = analytic
        invoice = inv.save()
        return invoice
