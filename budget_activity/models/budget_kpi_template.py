# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class BudgetKPI(models.Model):
    _inherit = "budget.template.line"

    activity_ids = fields.Many2many(
        comodel_name="budget.activity",
        relation="budget_kpi_activity_rel",
        column1="budget_kpi_id",
        column2="activity_id",
        ondelete="restrict",
        required=True,
    )

    @api.onchange("kpi_id")
    def _onchange_kpi_id(self):
        self.activity_ids = self.kpi_id.activity_ids.ids

    @api.onchange("activity_ids")
    def _onchange_account_ids(self):
        self.account_ids = self.activity_ids.mapped("account_id").ids
