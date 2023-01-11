# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from freezegun import freeze_time

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import Form

from odoo.addons.budget_control.tests.common import BudgetControlCommon
from odoo.addons.operating_unit.tests.test_operating_unit import TestOperatingUnit


@tagged("post_install", "-at_install")
class TestBudgetControlOperatingUnit(BudgetControlCommon, TestOperatingUnit):
    @classmethod
    @freeze_time("2001-02-01")
    def setUpClass(cls):
        super().setUpClass()
        cls.BudgetTransfer = cls.env["budget.transfer"]
        cls.BudgetMoveAdjustment = cls.env["budget.move.adjustment"]
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
        # Assign budget.control amount: KPI1 = 100x4=400, KPI2=800, KPI3=1,200
        cls.budget_control.line_ids.filtered(lambda x: x.kpi_id == cls.kpi1).write(
            {"amount": 100}
        )
        cls.budget_control.line_ids.filtered(lambda x: x.kpi_id == cls.kpi2).write(
            {"amount": 200}
        )
        cls.budget_control.line_ids.filtered(lambda x: x.kpi_id == cls.kpi3).write(
            {"amount": 300}
        )
        cls.main_ou = cls.env.ref("operating_unit.main_operating_unit")
        cls.b2c_ou = cls.env.ref("operating_unit.b2c_operating_unit")

    @freeze_time("2001-02-01")
    def test_01_budget_control_operating_unit(self):
        """
        - Budget control has operating unit following analytic account
        - Budget control has 1 operating unit only
        """
        # Control budget
        self.budget_control.allocated_amount = 2400.0
        self.budget_control.action_done()
        self.budget_period.control_budget = True
        self.assertFalse(self.costcenter1.operating_unit_ids)
        self.assertFalse(self.budget_control.operating_unit_id)
        # analytic account must have 1 operating unit only
        with self.assertRaises(UserError):
            self.costcenter1.operating_unit_ids = [
                (4, self.main_ou.id),
                (4, self.b2c_ou.id),
            ]
            self.assertEqual(
                self.budget_control.operating_unit_id,
                self.costcenter1.operating_unit_ids,
            )
        self.costcenter1.operating_unit_ids = [(4, self.main_ou.id)]
        self.assertEqual(
            self.budget_control.operating_unit_id, self.costcenter1.operating_unit_ids
        )
        bill1 = self._create_simple_bill(self.costcenter1, self.account_kpi1, 100)
        bill1.action_post()
        self.assertEqual(bill1.state, "posted")

    @freeze_time("2001-02-01")
    def test_03_budget_transfer(self):
        """
        - Transfer with same operating unit
        - Transfer with difference operating unit
        """
        self.budget_period.control_budget = True
        # Control budget main ou
        self.budget_control.allocated_amount = 2400.0
        self.costcenter1.operating_unit_ids = [(4, self.main_ou.id)]
        self.assertEqual(
            self.budget_control.operating_unit_id, self.costcenter1.operating_unit_ids
        )

        # Create sample Budget Control and Control with B2B ou
        self.budget_control_b2c_ou = self.BudgetControl.create(
            {
                "name": "CostCenter1_b2c/%s" % self.year,
                "template_id": self.budget_period.template_id.id,
                "budget_period_id": self.budget_period.id,
                "analytic_account_id": self.costcenterX.id,
                "plan_date_range_type_id": self.date_range_type.id,
                "allocated_amount": 2400.0,
                "template_line_ids": [
                    self.template_line1.id,
                    self.template_line2.id,
                    self.template_line3.id,
                ],
            }
        )
        self.budget_control_b2c_ou.prepare_budget_control_matrix()
        assert len(self.budget_control_b2c_ou.line_ids) == 12
        self.budget_control_b2c_ou.line_ids.filtered(
            lambda x: x.kpi_id == self.kpi1
        ).write({"amount": 100})
        self.budget_control_b2c_ou.line_ids.filtered(
            lambda x: x.kpi_id == self.kpi2
        ).write({"amount": 200})
        self.budget_control_b2c_ou.line_ids.filtered(
            lambda x: x.kpi_id == self.kpi3
        ).write({"amount": 300})
        self.budget_control_b2c_ou.flush()
        self.costcenterX.operating_unit_ids = [(4, self.b2c_ou.id)]
        self.assertEqual(
            self.budget_control_b2c_ou.operating_unit_id,
            self.costcenterX.operating_unit_ids,
        )

        # Create budget transfer from
        transfer = self.BudgetTransfer.create({})
        with Form(transfer.transfer_item_ids) as line:
            line.transfer_id = transfer
            line.budget_control_from_id = self.budget_control
            line.budget_control_to_id = self.budget_control_b2c_ou
        transfer_line = line.save()
        transfer_line.amount = 500.0
        self.assertEqual(transfer_line.amount_from_available, 2400.0)
        self.assertEqual(transfer_line.amount_to_available, 2400.0)
        self.assertEqual(len(transfer.operating_unit_ids), 2)
        self.assertEqual(
            transfer.operating_unit_from, self.budget_control.operating_unit_id.name
        )
        self.assertEqual(
            transfer.operating_unit_to,
            self.budget_control_b2c_ou.operating_unit_id.name,
        )

        # Test search budget control with operating unit
        self.user2.default_operating_unit_id = self.b2c_ou.id
        self.env.ref("budget_control.group_budget_control_user").write(
            {"users": [(4, self.user2.id)]}
        )
        # Admin can see all ou (main and b2c)
        all_budget = self.BudgetControl.search([])
        self.assertEqual(len(all_budget), 2)
        # User can see b2c only
        budget_b2c = self.BudgetControl.with_user(self.user2).search([])
        self.assertEqual(len(budget_b2c), 1)
        # User can see all ou, if view with budget transfer
        all_budget_from_transfer = (
            self.BudgetControl.with_context(budget_transfer_access_sudo=1)
            .with_user(self.user2)
            .search([])
        )
        self.assertEqual(len(all_budget_from_transfer), 2)
        # User can't search main ou
        search_budget = self.budget_control.with_user(self.user2).name_search("Cost")
        self.assertEqual(len(search_budget), 1)
        # User can search main ou, if view with budget transfer
        search_budget = (
            self.budget_control.with_context(budget_transfer_access_sudo=1)
            .with_user(self.user2)
            .name_search("Cost")
        )
        self.assertEqual(len(search_budget), 2)

    @freeze_time("2001-02-01")
    def test_04_budget_move_adjustment(self):
        """Adjust with operating unit"""
        self.budget_period.control_budget = True
        # Control budget main ou
        self.budget_control.allocated_amount = 2400.0
        self.budget_control.action_done()
        self.costcenter1.operating_unit_ids = [(4, self.main_ou.id)]
        self.assertEqual(
            self.budget_control.operating_unit_id, self.costcenter1.operating_unit_ids
        )

        # Create budget move adjustment
        adjust_budget = self.BudgetMoveAdjustment.create({"date_commit": "2001-02-01"})
        self.assertEqual(adjust_budget.operating_unit_id, self.main_ou)
        # Create line with difference ou must be error
        with self.assertRaises(UserError):
            with Form(adjust_budget.adjust_item_ids) as line:
                line.adjust_id = adjust_budget
                line.adjust_type = "consume"
                line.account_id = self.account_kpi1
                line.analytic_account_id = self.costcenter1
                line.amount = 100.0
                line.operating_unit_id = self.b2c_ou
            line.save()
        # Create line with same ou
        with Form(adjust_budget.adjust_item_ids) as line:
            line.adjust_id = adjust_budget
            line.adjust_type = "consume"
            line.account_id = self.account_kpi1
            line.analytic_account_id = self.costcenter1
            line.amount = 100.0
            line.operating_unit_id = self.main_ou
        adjust_line = line.save()
        self.assertEqual(adjust_line.operating_unit_id, adjust_budget.operating_unit_id)
