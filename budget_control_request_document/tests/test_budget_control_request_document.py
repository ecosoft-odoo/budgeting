# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from freezegun import freeze_time
from odoo_test_helper import FakeModelLoader

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.budget_control.tests.common import get_budget_common_class


@tagged("post_install", "-at_install")
class TestBudgetControlRequest(get_budget_common_class()):
    @classmethod
    @freeze_time("2001-02-01")
    def setUpClass(cls):
        super().setUpClass()
        # Create budget plan with 1 analytic
        lines = [
            Command.create(
                {"analytic_account_id": cls.costcenter1.id, "amount": 2400.0}
            )
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

        cls.budget_control = cls.budget_plan.budget_control_ids
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

        # Import tester module for request document
        cls.loader = FakeModelLoader(cls.env, cls.__module__)
        cls.loader.backup_registry()

        from odoo.addons.request_document.tests.request_document_tester import (
            RequestDocument,
        )

        cls.loader.update_registry((RequestDocument,))

        cls.request_obj = cls.env["request.order"]
        cls.move_model = cls.env["account.move"]

    @classmethod
    def tearDownClass(cls):
        cls.loader.restore_registry()
        super().tearDownClass()

    def test_01_budget_request_type_not_implemented(self):
        """
        Check Request Type is not implemented, it should raise error
        """
        # Controlled budget
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.assertAlmostEqual(self.budget_control.amount_budget, 2400.0)

        # Prepare Request
        request = self.request_obj.create(
            {"line_ids": [Command.create({"request_type": "tester"})]}
        )
        with self.assertRaisesRegex(
            UserError, "Request type 'tester' is not implemented"
        ):
            request.action_submit()

    @freeze_time("2001-02-01")
    def test_02_budget_request_commit_budget(self):
        """
        Request commit to destination document (Example is bill)
        """
        # Controlled budget
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.budget_period.control_budget = True
        self.budget_period.control_level = "analytic"
        self.assertTrue(self.budget_period.request_document)
        self.assertAlmostEqual(self.budget_control.amount_budget, 2400.0)

        # Import tester module for request document
        from .request_document_tester import (
            AccountMove,
            BudgetDoclineMixin,
            RequestDocument,
        )

        self.loader.update_registry((RequestDocument, AccountMove, BudgetDoclineMixin))

        # Prepare Request
        analytic_distribution = {self.costcenter1.id: 100}
        request_order = self.request_obj.create(
            {"line_ids": [Command.create({"request_type": "tester"})]}
        )
        # Create bill and link to request document
        bill1 = self._create_simple_bill(analytic_distribution, self.account_kpi1, 2401)
        bill1.request_document_id = request_order.line_ids.id

        self.assertEqual(len(request_order.line_ids), 1)
        self.assertEqual(len(request_order.line_ids.move_ids), 1)

        # kpi 1 (kpi1) & CostCenter1, will result in $ -1.00
        with self.assertRaisesRegex(UserError, "Budget not sufficient"):
            request_order.action_submit()
        request_order.action_draft()
        self.assertEqual(request_order.state, "draft")

        bill1.invoice_line_ids.write({"price_unit": 1800})
        request_order.action_submit()
        self.assertEqual(request_order.state, "submit")
        self.assertFalse(request_order.line_ids.line_data_amount)
        request_order.action_approve()
        self.assertEqual(request_order.state, "approve")
        self.assertEqual(bill1.state, "draft")
        self.assertTrue(request_order.line_ids.line_data_amount)
        self.assertEqual(len(request_order.budget_move_ids), 1)
        self.assertAlmostEqual(self.budget_control.amount_balance, 600.0)  # 2400 - 1800
        self.assertAlmostEqual(self.budget_control.amount_request, 1800.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 0.0)

        request_order.action_process_document()
        self.assertEqual(len(request_order.budget_move_ids), 2)
        self.assertAlmostEqual(self.budget_control.amount_balance, 600.0)  # 2400 - 1800
        self.assertAlmostEqual(self.budget_control.amount_request, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 1800.0)
        self.assertEqual(bill1.state, "posted")
        self.assertEqual(request_order.state, "done")

        # Check close budget move on request order, it will nothing to do
        request_order.close_budget_move()
        self.assertEqual(len(request_order.budget_move_ids), 2)
        self.assertAlmostEqual(self.budget_control.amount_balance, 600.0)  # 2400 - 1800
        self.assertAlmostEqual(self.budget_control.amount_request, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 1800.0)

    @freeze_time("2001-02-01")
    def test_03_budget_request_change_amount_document(self):
        """
        Change amount document after approved
        """
        # Controlled budget
        self.budget_control.action_submit()
        self.budget_control.action_done()
        self.budget_period.control_budget = True
        self.budget_period.control_level = "analytic"
        self.assertTrue(self.budget_period.request_document)
        self.assertAlmostEqual(self.budget_control.amount_budget, 2400.0)

        # Import tester module for request document
        from .request_document_tester import (
            AccountMove,
            BudgetDoclineMixin,
            RequestDocument,
        )

        self.loader.update_registry((RequestDocument, AccountMove, BudgetDoclineMixin))

        # Prepare Request
        analytic_distribution = {self.costcenter1.id: 100}
        request_order = self.request_obj.create(
            {"line_ids": [Command.create({"request_type": "tester"})]}
        )
        # Create bill and link to request document
        bill1 = self._create_simple_bill(analytic_distribution, self.account_kpi1, 1800)
        bill1.request_document_id = request_order.line_ids.id

        self.assertEqual(len(request_order.line_ids), 1)
        self.assertEqual(len(request_order.line_ids.move_ids), 1)
        self.assertEqual(request_order.state, "draft")

        request_order.action_submit()
        self.assertEqual(request_order.state, "submit")
        self.assertFalse(request_order.line_ids.line_data_amount)

        request_order.action_approve()
        self.assertEqual(request_order.state, "approve")
        self.assertTrue(request_order.line_ids.line_data_amount)
        self.assertEqual(bill1.state, "draft")

        # Line data amount should be empty when cancel or draft
        request_order.action_cancel()
        self.assertEqual(request_order.state, "cancel")
        self.assertFalse(request_order.line_ids.line_data_amount)

        request_order.action_draft()
        request_order.action_submit()
        request_order.action_approve()

        self.assertEqual(len(request_order.budget_move_ids), 1)
        self.assertAlmostEqual(self.budget_control.amount_balance, 600.0)  # 2400 - 1800
        self.assertAlmostEqual(self.budget_control.amount_request, 1800.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 0.0)

        request_order.action_process_document()
        self.assertEqual(len(request_order.budget_move_ids), 2)
        self.assertAlmostEqual(self.budget_control.amount_balance, 600.0)  # 2400 - 1800
        self.assertAlmostEqual(self.budget_control.amount_request, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 1800.0)
        self.assertEqual(bill1.state, "posted")
        self.assertEqual(request_order.state, "done")

        # Test changed amount document, Request budget should uncommit same value
        bill1.button_draft()
        bill1.invoice_line_ids.write({"price_unit": 500.0})
        bill1.action_post()
        request_order.recompute_budget_move()
        self.assertEqual(len(request_order.budget_move_ids), 2)
        self.assertAlmostEqual(self.budget_control.amount_balance, 1900.0)  # 2400 - 500
        self.assertAlmostEqual(self.budget_control.amount_request, 0.0)
        self.assertAlmostEqual(self.budget_control.amount_actual, 500.0)
