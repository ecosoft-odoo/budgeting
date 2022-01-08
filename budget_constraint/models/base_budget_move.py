# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.exceptions import UserError


class BudgetDoclineMixin(models.AbstractModel):
    _inherit = "budget.docline.mixin"

    def _get_budget_constraint(self):
        return self.env["budget.constraint"].search([], order="sequence")

    @api.model
    def check_budget_constraint(self, budget_constraints):
        message = []
        for budget_constraint in budget_constraints:
            result = (
                budget_constraint.server_action_id.with_context(
                    active_model=budget_constraint._name,
                    active_id=budget_constraint.id,
                    doclines=self,
                )
                .sudo()
                .run()
            )
            if result:
                message.extend(result)
        return message

    def commit_budget(self, reverse=False, **vals):
        """Create budget commit for each docline"""
        budget_move = super().commit_budget(reverse=reverse, **vals)
        budget_constraints = self._get_budget_constraint()
        if budget_move and budget_constraints:
            message = self.check_budget_constraint(budget_constraints)
            if message:
                raise UserError(_("\n".join(message)))
        return budget_move
