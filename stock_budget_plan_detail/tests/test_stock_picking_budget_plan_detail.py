# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

from odoo import Command

from odoo.addons.budget_plan_detail.tests.test_budget_plan_detail import (
    TestBudgetPlanDetail,
)
from odoo.addons.stock_analytic.tests.test_stock_picking import TestStockPicking

from ..hooks import uninstall_hook


class TestStockPickingBudgetPlanDetail(TestBudgetPlanDetail, TestStockPicking):
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

        # Create dimension
        cls.analytic_line_obj = cls.env["account.analytic.line"]
        cls.dimension_obj = cls.env["account.analytic.dimension"]
        cls.dimension_1 = cls.dimension_obj.create(
            {"name": "Test dimension 1", "code": "test_dim_1"}
        )

    def test_01_incoming_picking_with_budget(self):
        analytic_distribution = {self.costcenter1.id: 100}
        picking = self._create_picking(
            self.location,
            self.dest_location,
            self.incoming_picking_type,
            analytic_distribution,
        )
        picking.move_ids.write(
            {
                "fund_id": self.fund1_g1.id,
                "analytic_tag_ids": [Command.set(self.analytic_tag1.ids)],
            }
        )

        picking_move = picking.move_ids

        self.assertEqual(picking_move.fund_id, self.fund1_g1)
        self.assertEqual(picking_move.analytic_tag_ids, self.analytic_tag1)
        self.assertEqual(picking.state, "draft")
        self._update_qty_on_hand_product(self.product, 1)

        self.assertFalse(picking.move_line_ids)
        self._confirm_picking_no_error(picking)
        self.assertEqual(picking.move_line_ids.fund_id, self.fund1_g1)
        self.assertEqual(picking.move_line_ids.analytic_tag_ids, self.analytic_tag1)
        self._picking_done_no_error(picking)

        # Check Account (Perpetual)
        criteria1 = [["ref", "=", f"{picking.name} - {picking.product_id.name}"]]
        acc_moves = self.env["account.move"].search(criteria1)

        self.assertEqual(len(acc_moves), 1)
        # Move must have not affect budget only
        self.assertEqual(acc_moves.not_affect_budget, True)
        acc_lines = acc_moves.line_ids
        move = picking.move_ids[0]
        for acc_line in acc_lines:
            if acc_line.account_id == self.valuation_account:
                self.assertFalse(acc_line.fund_id)
                self.assertFalse(acc_line.analytic_tag_ids)
            else:
                self.assertEqual(acc_line.fund_id, move.fund_id)
                self.assertEqual(acc_line.analytic_tag_ids, move.analytic_tag_ids)

        # Check stock.move.line mush have fund, analytic tags from stock.move
        for move_line in picking.move_line_ids:
            self.assertEqual(move_line.fund_id, move_line.move_id.fund_id)
            self.assertEqual(
                move_line.analytic_tag_ids, move_line.move_id.analytic_tag_ids
            )

    def test_02_picking_add_extra_move_line(self):
        """
        Create stock movee line direct,
        Stock Move should create with fund, analytic tags from move line
        """
        picking = self._create_picking(
            self.location,
            self.dest_location,
            self.outgoing_picking_type,
            self.analytic_distribution,
        )
        move_before = picking.move_ids

        self.env["stock.move.line"].create(
            {
                "product_id": self.product_2.id,
                "location_id": self.location.id,
                "location_dest_id": self.dest_location.id,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "product_uom_id": self.product_2.uom_id.id,
                "analytic_distribution": self.analytic_distribution,
                "fund_id": self.fund1_g1.id,
                "analytic_tag_ids": [Command.set(self.analytic_tag1.ids)],
                "company_id": self.env.company.id,
                "picking_id": picking.id,
            }
        )

        move_after = picking.move_ids - move_before

        self.assertEqual(move_after.fund_id, self.fund1_g1)
        self.assertEqual(move_after.analytic_tag_ids, self.analytic_tag1)

    def test_03_procurement_with_budget(self):
        src_location, dst_location = self._replace_default_mto_route()
        picking = self._create_picking(
            src_location,
            dst_location,
            self.outgoing_picking_type,
            self.analytic_distribution,
            procure_method="make_to_order",
        )
        picking.move_ids.write(
            {
                "fund_id": self.fund1_g1.id,
                "analytic_tag_ids": [Command.set(self.analytic_tag1.ids)],
            }
        )
        picking.action_confirm()
        procured_moves = picking.move_ids.move_orig_ids
        self.assertTrue(procured_moves)
        for move in procured_moves:
            self.assertEqual(
                move.fund_id,
                self.fund1_g1,
                msg="In MTO procurement, the fund should propagate",
            )
            self.assertEqual(
                move.analytic_tag_ids,
                self.analytic_tag1,
                msg="In MTO procurement, the analytic tag should propagate",
            )

    def test_04_remove_dimension(self):
        self.dimension_1.unlink()
        self.assertNotIn("x_dimension_test_dim_1", self.analytic_line_obj._fields)
        uninstall_hook(self.env)
        self.assertNotIn("x_dimension_test_dim_2", self.analytic_line_obj._fields)
