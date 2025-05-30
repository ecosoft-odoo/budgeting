# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BudgetCommonMonitoring(models.AbstractModel):
    _name = "budget.common.monitoring"
    _description = "Budget Common Monitoring"

    res_id = fields.Reference(
        selection=lambda self: [("budget.control.line", "Budget Control Lines")]
        + self._get_budget_docline_model(),
        string="Resource ID",
    )
    reference = fields.Char()
    amount_type = fields.Selection(
        selection=lambda self: [("10_budget", "Budget")]
        + self._get_budget_amount_type(),
        string="Type",
    )
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
    )
    budget_period_id = fields.Many2one(
        comodel_name="budget.period",
    )
    active = fields.Boolean()
    amount = fields.Float()

    def _get_budget_amount_type(self):
        """Return list of all amount_type selection"""
        return [x["type"] for x in self._get_consumed_sources()]

    def _get_budget_docline_model(self):
        """Return list of all res_id models selection"""
        return [x["model"] for x in self._get_consumed_sources()]

    def _get_consumed_sources(self):
        return [
            {
                "model": ("account.move.line", "Account Move Line"),
                "type": ("80_actual", "Actual"),
                "budget_move": ("account_budget_move", "move_line_id"),
                "source_doc": ("account_move", "move_id"),
            }
        ]
