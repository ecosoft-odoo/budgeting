# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command

from odoo.addons.budget_plan_detail.tests.test_budget_plan_detail import (
    TestBudgetPlanDetail,
)
from odoo.addons.stock_analytic.tests.test_stock_picking import CommonStockPicking


class TestStockScrapBudgetPlanDetail(TestBudgetPlanDetail, CommonStockPicking):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # cls.product_categ = cls.env.ref("product.product_category_5")
        # print(cls.product.categ_id)
        # print("-x---")

    def test_01_scrap_with_budget(self):
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

        # ====== Start Create Scrap ======
        qty_wizard = self.env["stock.change.product.qty"].create(
            {
                "product_id": self.product.id,
                "product_tmpl_id": self.product.product_tmpl_id.id,
                "new_quantity": 1,
            }
        )
        qty_wizard.change_product_qty()

        # Create scrap
        analytic_distribution = {self.costcenter1.id: 100}
        scrap_data = {
            "product_id": self.product.id,
            "scrap_qty": 1.00,
            "product_uom_id": self.product.uom_id.id,
            "location_id": self.location.id,
            "analytic_distribution": analytic_distribution,
            "fund_id": self.fund1_g1.id,
            "analytic_tag_ids": [Command.set(self.analytic_tag1.ids)],
        }

        scrap = self.env["stock.scrap"].create(scrap_data)
        scrap.action_validate()
        self.assertEqual(scrap.state, "done")

        # Check Account (Perpetual)
        domain = [("ref", "=", f"{scrap.name} - {self.product.name}")]
        acc_move = self.env["account.move"].search(domain)
        self.assertEqual(len(acc_move), 1)
        self.assertEqual(acc_move.not_affect_budget, True)

        acc_lines = acc_move.line_ids
        for acc_line in acc_lines:
            if (
                acc_line.account_id
                != scrap.product_id.categ_id.property_stock_valuation_account_id
            ):
                self.assertEqual(acc_line.fund_id, scrap.fund_id)
                self.assertEqual(acc_line.analytic_tag_ids, scrap.analytic_tag_ids)
