# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from freezegun import freeze_time

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import Form, tagged

from odoo.addons.budget_control.tests.common import get_budget_common_class
from odoo.addons.operating_unit.tests.test_operating_unit import TestOperatingUnit


@tagged("post_install", "-at_install")
class TestBudgetControlOperatingUnit(get_budget_common_class(), TestOperatingUnit):
    @classmethod
    @freeze_time("2001-02-01")
    def setUpClass(cls):
        super().setUpClass()
        cls.main_ou = cls.env.ref("operating_unit.main_operating_unit")
        cls.b2c_ou = cls.env.ref("operating_unit.b2c_operating_unit")

        # Create budget plan with 1 analytic
        lines = [
            Command.create(
                {"analytic_account_id": cls.costcenter1.id, "amount": 2400.0}
            ),
            Command.create(
                {"analytic_account_id": cls.costcenterX.id, "amount": 2400.0}
            ),
        ]
        cls.budget_plan = cls.create_budget_plan(
            cls,
            name="Test - Plan {cls.budget_period.name}",
            budget_period=cls.budget_period,
            lines=lines,
        )
        cls.budget_plan.action_confirm()
        cls.budget_plan.action_create_update_budget_control()
        cls.budget_plan.action_done()

        # Refresh data
        cls.budget_plan.invalidate_recordset()

        cls.budget_control = cls.budget_plan.budget_control_ids[0]
        cls.budget_control.template_line_ids = [
            cls.template_line1.id,
            cls.template_line2.id,
            cls.template_line3.id,
        ]

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

        # Budget Control2
        cls.budget_control2 = cls.budget_plan.budget_control_ids[1]
        cls.budget_control2.template_line_ids = [
            cls.template_line1.id,
            cls.template_line2.id,
            cls.template_line3.id,
        ]

        # Test item created for 3 kpi x 4 quarters = 12 budget items
        cls.budget_control2.prepare_budget_control_matrix()
        assert len(cls.budget_control2.line_ids) == 12
        # Assign budget.control amount: KPI1 = 100x4=400, KPI2=800, KPI3=1,200
        cls.budget_control2.line_ids.filtered(lambda x: x.kpi_id == cls.kpi1).write(
            {"amount": 100}
        )
        cls.budget_control2.line_ids.filtered(lambda x: x.kpi_id == cls.kpi2).write(
            {"amount": 200}
        )
        cls.budget_control2.line_ids.filtered(lambda x: x.kpi_id == cls.kpi3).write(
            {"amount": 300}
        )

    @freeze_time("2001-02-01")
    def test_01_budget_control_operating_unit(self):
        """
        - Budget control has operating unit following analytic account
        - Budget control has 1 operating unit only
        """
        # Controlled budget
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.assertAlmostEqual(self.budget_control.amount_budget, 2400.0)

        self.assertFalse(self.costcenter1.operating_unit_ids)
        self.assertFalse(self.budget_control.operating_unit_id)

        # analytic account must have 1 operating unit only
        with self.assertRaisesRegex(
            UserError, "Analytic Account can't select operating unit > 1"
        ):
            self.costcenter1.operating_unit_ids = [
                (4, self.main_ou.id),
                (4, self.b2c_ou.id),
            ]
            self.assertEqual(
                self.budget_control.operating_unit_id,
                self.costcenter1.operating_unit_ids,
            )
        self.costcenter1.operating_unit_ids = self.main_ou
        self.assertEqual(
            self.budget_control.operating_unit_id, self.costcenter1.operating_unit_ids
        )
        analytic_distribution = {self.costcenter1.id: 100}
        bill1 = self._create_simple_bill(analytic_distribution, self.account_kpi1, 100)
        bill1.line_ids.write(
            {"operating_unit_id": self.budget_control.operating_unit_id.id}
        )
        bill1.action_post()
        self.assertEqual(bill1.state, "posted")
        self.assertEqual(
            bill1.budget_move_ids.operating_unit_id,
            self.budget_control.operating_unit_id,
        )

    @freeze_time("2001-02-01")
    def test_02_budget_transfer_multi_ou(self):
        """Transfer with difference operating unit"""
        self.costcenter1.operating_unit_ids = [Command.set(self.main_ou.ids)]
        self.assertEqual(
            self.budget_control.operating_unit_id, self.costcenter1.operating_unit_ids
        )

        self.costcenterX.operating_unit_ids = [Command.set(self.b2c_ou.ids)]
        self.assertEqual(
            self.budget_control2.operating_unit_id, self.costcenterX.operating_unit_ids
        )

        # Create budget transfer from
        transfer = self._create_budget_transfer(
            self.budget_control, self.budget_control2, 500.0
        )

        self.assertEqual(len(transfer.transfer_item_ids), 1)
        self.assertEqual(len(transfer.operating_unit_ids), 2)
        self.assertEqual(
            transfer.operating_unit_from, self.budget_control.operating_unit_id.name
        )
        self.assertEqual(
            transfer.operating_unit_to,
            self.budget_control2.operating_unit_id.name,
        )

    @freeze_time("2001-02-01")
    def test_03_budget_transfer_same_ou(self):
        """Transfer with same operating unit"""
        self.costcenter1.operating_unit_ids = [Command.set(self.main_ou.ids)]
        self.assertEqual(
            self.budget_control.operating_unit_id, self.costcenter1.operating_unit_ids
        )

        self.costcenterX.operating_unit_ids = [Command.set(self.main_ou.ids)]
        self.assertEqual(
            self.budget_control2.operating_unit_id, self.costcenterX.operating_unit_ids
        )

        # Create budget transfer from
        transfer = self._create_budget_transfer(
            self.budget_control, self.budget_control2, 500.0
        )

        self.assertEqual(len(transfer.transfer_item_ids), 1)
        self.assertEqual(len(transfer.operating_unit_ids), 1)
        self.assertEqual(
            transfer.operating_unit_from, self.budget_control.operating_unit_id.name
        )
        self.assertEqual(
            transfer.operating_unit_to,
            self.budget_control2.operating_unit_id.name,
        )

    @freeze_time("2001-02-01")
    def test_04_budget_move_adjustment(self):
        """Adjust with operating unit"""
        # Controlled budget
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.assertAlmostEqual(self.budget_control.amount_budget, 2400.0)

        self.assertFalse(self.costcenter1.operating_unit_ids)
        self.assertFalse(self.budget_control.operating_unit_id)

        self.costcenter1.operating_unit_ids = [Command.set(self.main_ou.ids)]
        self.assertEqual(
            self.budget_control.operating_unit_id, self.costcenter1.operating_unit_ids
        )

        # Create budget move adjustment
        adjust_budget = self.BudgetAdjust.create({"date_commit": "2001-02-01"})
        self.assertEqual(adjust_budget.operating_unit_id, self.main_ou)
        # Create line with difference ou must be error
        with self.assertRaisesRegex(
            UserError,
            "The Operating Unit in the Line and in the Adjustment must be the same.",
        ):
            with Form(adjust_budget.adjust_item_ids) as line:
                line.adjust_id = adjust_budget
                line.adjust_type = "consume"
                line.account_id = self.account_kpi1
                line.analytic_distribution = {self.costcenter1.id: 100}
            line.amount = 100.0
            line.operating_unit_id = self.b2c_ou
            line.save()
        # Create line with same ou
        with Form(adjust_budget.adjust_item_ids) as line:
            line.adjust_id = adjust_budget
            line.adjust_type = "consume"
            line.account_id = self.account_kpi1
            line.analytic_distribution = {self.costcenter1.id: 100}
            line.amount = 100.0
            line.operating_unit_id = self.main_ou
        adjust_line = line.save()
        self.assertEqual(adjust_line.operating_unit_id, adjust_budget.operating_unit_id)
