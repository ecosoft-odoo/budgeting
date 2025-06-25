# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command

from odoo.addons.budget_plan_detail.tests.test_budget_plan_detail import (
    TestBudgetPlanDetail,
)
from odoo.addons.purchase_stock_analytic.tests.test_purchase_stock_analytic import (
    TestPurchaseStockAnalytic,
)


class TestPurchaseStockBudgetPlanDetail(
    TestPurchaseStockAnalytic, TestBudgetPlanDetail
):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create same analytic, difference fund, difference analytic tags
        # line 1: Costcenter1, Fund1, Tag1, 600.0
        # line 2: Costcenter1, Fund1, Tag2, 600.0
        # line 3: Costcenter1, Fund2, Tag1, 600.0
        # line 4: Costcenter1, Fund2,     , 600.0
        # line 5: CostcenterX, Fund1, Tag1, 600.0
        # line 6: CostcenterX, Fund2, Tag1, 600.0
        # line 7: CostcenterX, Fund2, Tag2, 600.0
        # line 8: CostcenterX, Fund1,     , 600.0
        cls._create_budget_plan_line_detail(cls, cls.budget_plan)
        cls.budget_plan.action_confirm_plan_detail()
        cls.budget_plan.action_confirm()
        cls.budget_plan.action_create_update_budget_control()
        cls.budget_plan.action_done()

        # Refresh data and Prepare budget control
        cls.budget_plan.invalidate_recordset()
        # Get 1 budget control, Costcenter1 has 4 plan detail
        budget_control = cls.budget_plan.budget_control_ids[0]
        budget_control.template_line_ids = [
            cls.template_line1.id,
            cls.template_line2.id,
            cls.template_line3.id,
        ]

        # Test item created for 3 kpi x 4 quarters = 12 budget items
        budget_control.prepare_budget_control_matrix()
        assert len(budget_control.line_ids) == 12
        # Costcenter1 has 3 plan detail
        # Assign budget.control amount: KPI1 = 1500, 500, 400
        bc_items = budget_control.line_ids.filtered(lambda x: x.kpi_id == cls.kpi1)
        bc_items[0].write({"amount": 1500})
        bc_items[1].write({"amount": 500})
        bc_items[2].write({"amount": 400})

        # Control budget
        budget_control.action_submit()
        budget_control.action_done()
        cls.budget_period.control_budget = True

    def test_01_purchase_stock_budget(self):
        analytic_distribution = {self.costcenter1.id: 100}

        po_with_budget = self.purchase_order_model.create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    Command.create(
                        {
                            "name": "purchase order line test",
                            "product_qty": 3,
                            "price_unit": 20,
                            "product_id": self.product1.id,
                            "analytic_distribution": analytic_distribution,
                            "fund_id": self.fund1_g1.id,
                            "analytic_tag_ids": [Command.set(self.analytic_tag1.ids)],
                        }
                    )
                ],
            }
        )

        po_line = po_with_budget.order_line

        self.assertEqual(po_line.fund_id, self.fund1_g1)
        self.assertEqual(po_line.analytic_tag_ids, self.analytic_tag1)
        po_with_budget.button_confirm()

        self.move = po_with_budget.picking_ids.move_ids_without_package
        self.assertEqual(self.move.fund_id, self.fund1_g1)
        self.assertEqual(self.move.analytic_tag_ids, self.analytic_tag1)
