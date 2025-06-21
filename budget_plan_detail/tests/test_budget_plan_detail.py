# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from freezegun import freeze_time

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import BudgetPlanDetailCommon


@tagged("post_install", "-at_install")
class TestBudgetPlanDetail(BudgetPlanDetailCommon):
    @classmethod
    @freeze_time("2001-02-01")
    def setUpClass(cls):
        super().setUpClass()
        cls.BudgetTransfer = cls.env["budget.transfer"]

        # Active check budget detail over limit
        cls.env.ref("budget_plan_detail.check_budget_detail_over_limit").write(
            {"active": True}
        )

        # Add period on analytic account
        cls.costcenter1.write({"budget_period_id": cls.budget_period.id})
        cls.costcenterX.write({"budget_period_id": cls.budget_period.id})

        # Create empty budget plan
        cls.budget_plan = cls.create_budget_plan(
            cls,
            name="Test - Plan {cls.budget_period.name}",
            budget_period=cls.budget_period,
            lines=[],
            skip_line_detail=True,
        )

        cls.analytic_demo = (
            cls.env.ref("analytic_tag_dimension.analytic_tag_type_a")
            + cls.env.ref("analytic_tag_dimension.analytic_tag_type_b")
            + cls.env.ref("analytic_tag_dimension.analytic_tag_concept_a")
            + cls.env.ref("analytic_tag_dimension.analytic_tag_concept_b")
        )

    def test_01_master_data_source_fund(self):
        self.assertEqual(self.fund1_g1.name, "Test Fund 1")
        self.fund1_g1_copy = self.fund1_g1.copy()
        self.assertEqual(self.fund1_g1_copy.name, "Test Fund 1 (copy)")

    @freeze_time("2001-02-01")
    def test_02_budget_plan_detail_process(self):
        self.assertFalse(self.budget_plan.line_detail_ids)
        self.assertFalse(self.budget_plan.line_ids)

        self._create_budget_plan_line_detail(self.budget_plan, auto_confirm=False)

        self.assertAlmostEqual(self.budget_plan.total_amount, 4800.0)
        self.assertEqual(len(self.budget_plan.line_detail_ids), 8)
        self.assertFalse(self.budget_plan.is_confirm_plan)
        # Budget Plan line still not created (first time)
        self.assertFalse(self.budget_plan.line_ids)
        self.assertFalse(self.budget_plan.line_detail_ids[0].plan_line_id)

        # Estimated amount should be equal to allocated amount
        self.assertEqual(
            self.budget_plan.line_detail_ids[0].estimated_amount,
            self.budget_plan.line_detail_ids[0].allocated_amount,
        )
        self.assertEqual(
            sum(self.budget_plan.line_detail_ids.mapped("allocated_amount")),
            self.budget_plan.total_amount,
        )
        self.assertEqual(
            sum(self.budget_plan.line_detail_ids.mapped("released_amount")), 0.0
        )

        self.budget_plan.action_confirm_plan_detail()

        # After confirm detail, plan line should be created
        self.assertTrue(self.budget_plan.is_confirm_plan)
        self.assertEqual(len(self.budget_plan.line_detail_ids), 8)
        self.assertEqual(len(self.budget_plan.line_ids), 2)

        # Check Link button budget plan to budget plan detail
        action = self.budget_plan.button_open_budget_plan_detail()
        self.assertEqual(action["res_model"], "budget.plan.line.detail")

        # Check Link button budget plan line to budget plan detail
        action = self.budget_plan.line_ids[0].open_plan_line_detail()
        self.assertEqual(action["res_model"], "budget.plan.line.detail")

        # Cancel plan detail
        self.budget_plan.action_cancel_plan_detail()
        self.assertFalse(self.budget_plan.is_confirm_plan)

        self.budget_plan.action_confirm_plan_detail()
        self.assertTrue(self.budget_plan.is_confirm_plan)
        self.assertTrue(self.budget_plan.line_detail_ids[0].plan_line_id)

        self.budget_plan.action_confirm()
        self.assertEqual(self.budget_plan.state, "confirm")
        self.budget_plan.action_create_update_budget_control()
        self.budget_plan.action_done()

        self.assertEqual(self.budget_plan.state, "done")

    @freeze_time("2001-02-01")
    def test_03_budget_plan_check_edit_line(self):
        lines = [
            {
                "plan_id": self.budget_plan.id,
                "analytic_account_id": self.costcenter1.id,
                "fund_id": self.fund1_g1.id,
                "analytic_tag_ids": [(4, self.analytic_tag1.id)],
                "allocated_amount": 100.0,
            }
        ]

        self._create_budget_plan_line_detail(self.budget_plan, lines)
        self.budget_plan.action_confirm_plan_detail()
        self.assertTrue(self.budget_plan.is_confirm_plan)

        # Can't add new line detail, if budget plan is confirmed detail
        with self.assertRaisesRegex(
            UserError, "You cannot create a detail line for a confirmed plan."
        ):
            self._create_budget_plan_line_detail(self.budget_plan, lines)

        # Can't edit line detail, if budget plan is confirmed detail
        with self.assertRaisesRegex(
            UserError, "You cannot edit a detail line for a confirmed plan."
        ):
            self.budget_plan.line_detail_ids[0].write({"allocated_amount": 200.0})

        # Can edit line detail, if send context "allow_edit_plan_detail"
        self.assertAlmostEqual(
            self.budget_plan.line_detail_ids[0].allocated_amount, 100.0
        )
        self.budget_plan.line_detail_ids[0].with_context(
            allow_edit_plan_detail=1
        ).write({"allocated_amount": 200.0})
        self.assertAlmostEqual(
            self.budget_plan.line_detail_ids[0].allocated_amount, 200.0
        )

    @freeze_time("2001-02-01")
    def test_04_budget_plan_check_over_limit(self):
        self._create_budget_plan_line_detail(self.budget_plan)
        self.budget_plan.action_confirm_plan_detail()
        self.budget_plan.action_confirm()
        self.assertEqual(self.budget_plan.state, "confirm")
        self.budget_plan.action_create_update_budget_control()
        self.budget_plan.action_done()

        self.assertEqual(self.budget_plan.state, "done")

        # Refresh data and Prepare budget control
        self.budget_plan.invalidate_recordset()
        # Get 1 budget control, Costcenter1 has 4 plan detail by default
        # line 1: Costcenter1, Fund1, Tag1, 600.0
        # line 2: Costcenter1, Fund1, Tag2, 600.0
        # line 3: Costcenter1, Fund2, Tag1, 600.0
        # line 4: Costcenter1, Fund2,     , 600.0
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
        # Commit actual without allocation (no fund, no tags)
        # We allocate 600.0 to Costcenter1, but commit 601.0
        analytic_distribution = {self.costcenter1.id: 100}
        bill1 = self._create_simple_bill(
            analytic_distribution,
            self.account_kpi1,
            601,
            default_tag=False,
            default_fund=False,
        )
        with self.assertRaisesRegex(
            UserError, "is not allocated on budget plan detail"
        ):
            bill1.action_post()
        bill1.button_draft()

        # Add Fund1, Tag1 allocated 600.0
        bill1.invoice_line_ids.fund_id = self.fund1_g1.id
        bill1.invoice_line_ids.analytic_tag_ids = [(4, self.analytic_tag1.id)]
        # Actual amount 601 > allocated amount 600.0, it should error
        with self.assertRaisesRegex(
            UserError, "spend amount over budget plan detail limit"
        ):
            bill1.action_post()
        bill1.button_draft()

        # Change actual commit to 400.0
        bill1.invoice_line_ids.price_unit = 400.0
        bill1.action_post()

        # Check commit budget must have Fund and Tag
        self.assertTrue(bill1.budget_move_ids.analytic_tag_ids)
        self.assertEqual(bill1.budget_move_ids.fund_id, self.fund1_g1)

        # Next, commit 201.0 it should error
        bill2 = self._create_simple_bill(
            analytic_distribution,
            self.account_kpi1,
            201,
            default_tag=False,
            default_fund=False,
        )
        bill2.invoice_line_ids.fund_id = self.fund1_g1.id
        bill2.invoice_line_ids.analytic_tag_ids = [(4, self.analytic_tag1.id)]

        with self.assertRaisesRegex(
            UserError, "spend amount over budget plan detail limit"
        ):
            bill2.action_post()

    @freeze_time("2001-02-01")
    def test_05_transfer_budget_control(self):
        # budget control is depends on budget allocation
        self._create_budget_plan_line_detail(self.budget_plan, auto_confirm=False)
        self.budget_plan.action_confirm_plan_detail()
        self.budget_plan.action_confirm()
        self.assertEqual(self.budget_plan.state, "confirm")
        self.budget_plan.action_create_update_budget_control()
        self.budget_plan.action_done()

        self.assertEqual(len(self.budget_plan.line_ids), 2)
        self.assertEqual(self.budget_plan.state, "done")

        # Refresh data and Prepare budget control
        self.budget_plan.invalidate_recordset()
        budget_control_ids = self.budget_plan.budget_control_ids
        self.assertEqual(len(budget_control_ids), 2)
        for bc in budget_control_ids:
            bc.template_line_ids = [
                self.template_line1.id,
                self.template_line2.id,
                self.template_line3.id,
            ]

            # Test item created for 3 kpi x 4 quarters = 12 budget items
            bc.prepare_budget_control_matrix()
            assert len(bc.line_ids) == 12
            bc_items = bc.line_ids.filtered(lambda x: x.kpi_id == self.kpi1)
            # Assign budget.control amount: KPI1 = 1500, 500, 400
            bc_items[0].write({"amount": 1500})
            bc_items[1].write({"amount": 500})
            bc_items[2].write({"amount": 400})

        self.assertEqual(budget_control_ids[0].diff_amount, 0.0)
        self.assertEqual(budget_control_ids[1].diff_amount, 0.0)

        # Config dimension by sequence
        self.tag_dimension1.write({"by_sequence": True, "sequence": 1})

        # Transfer budget amount from line5 to line1
        # But test line 1 is selected analytic tags wrong
        # line 1: Costcenter1, Fund1, Tag1, 600.0
        # line 5: CostcenterX, Fund1, Tag1, 600.0
        transfer = self._create_budget_transfer(
            budget_control_ids[1], budget_control_ids[0], 500.0, analytic_tag_to=[]
        )

        transfer_line = transfer.transfer_item_ids
        # line 5 is correct
        self.assertEqual(len(transfer_line.detail_line_from_ids), 1)
        self.assertIn(transfer_line.fund_from_id, transfer_line.fund_from_all)
        self.assertEqual(transfer_line.analytic_tag_from_ids, self.analytic_tag1)
        self.assertEqual(
            transfer_line.analytic_tag_from_all, self.analytic_tag1 + self.analytic_tag2
        )
        self.assertTrue(transfer_line.domain_tag_from_ids)
        self.assertAlmostEqual(transfer_line.amount_from_available, 600.0)
        # line 1 must not found detail lines, amount will 0.0 too
        self.assertEqual(len(transfer_line.detail_line_to_ids), 0)
        self.assertIn(transfer_line.fund_to_id, transfer_line.fund_to_all)
        self.assertFalse(transfer_line.analytic_tag_to_ids)
        self.assertTrue(transfer_line.domain_tag_to_ids)
        self.assertEqual(
            budget_control_ids[0].analytic_tag_ids, transfer_line.analytic_tag_to_all
        )
        self.assertAlmostEqual(transfer_line.amount_to_available, 0.0)

        # Can't transfer because 'detail_line_to_ids' is not found
        with self.assertRaisesRegex(
            UserError, "Not found related budget detail lines!"
        ):
            transfer.action_submit()

        # Add Tag1 to line1
        transfer_line.analytic_tag_to_ids = [(4, self.analytic_tag1.id)]

        self.assertEqual(len(transfer_line.detail_line_to_ids), 1)
        self.assertAlmostEqual(transfer_line.amount_to_available, 600.0)

        transfer.action_submit()
        transfer.action_transfer()
        self.assertEqual(budget_control_ids[0].diff_amount, 500.0)
        self.assertEqual(budget_control_ids[1].diff_amount, -500.0)

        transfer.action_reverse()
        self.assertEqual(budget_control_ids[0].diff_amount, 0.0)
        self.assertEqual(budget_control_ids[1].diff_amount, 0.0)
