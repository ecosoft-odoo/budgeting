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

    def _update_budget_commitment(self, budget_vals, analytic, reverse=False):
        budget_vals = super()._update_budget_commitment(
            budget_vals, analytic, reverse=reverse
        )
        # docline's OU has priority over docline's header OU.
        if hasattr(self, "operating_unit_id"):
            budget_vals["operating_unit_id"] = self.operating_unit_id.id
        elif hasattr(self[self._doc_rel], "operating_unit_id"):
            budget_vals["operating_unit_id"] = self[self._doc_rel].operating_unit_id.id
        return budget_vals
