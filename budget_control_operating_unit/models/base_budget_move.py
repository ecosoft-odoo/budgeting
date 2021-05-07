# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class BaseBudgetMove(models.AbstractModel):
    _inherit = "base.budget.move"

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        index=True,
    )


class BudgetDoclineMixin(models.AbstractModel):
    _inherit = "budget.docline.mixin"

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        index=True,
    )

    def _update_budget_commitment(self, budget_vals, reverse=False):
        budget_vals = super()._update_budget_commitment(
            budget_vals, reverse=reverse
        )
        if self.operating_unit_id:
            ou_line = self.operating_unit_id.id
        else:
            # get ou from header if line not selected ou.
            ou_line = self[self._doc_rel].operating_unit_id.id
        budget_vals["operating_unit_id"] = ou_line
        return budget_vals
