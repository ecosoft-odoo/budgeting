# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BudgetCommonMonitoring(models.AbstractModel):
    _inherit = "budget.common.monitoring"

    fund_id = fields.Many2one(comodel_name="budget.source.fund")
    fund_group_id = fields.Many2one(comodel_name="budget.source.fund.group")

    def _get_dimension_fields(self, obj_name):
        return [x for x in self.env[obj_name]._fields if x.startswith("x_dimension_")]
