# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.exceptions import UserError


class BudgetPeriod(models.Model):
    _inherit = "budget.period"

    def _get_budget_constraint(self):
        return self.env["budget.constraint"].search(
            [("active", "=", True)], order="sequence"
        )

    @api.model
    def check_budget_constraint(self, budget_constraints, doclines):
        all_msg_error = ""
        for budget_constraint in budget_constraints:
            msg_error = (
                budget_constraint.server_action_id.with_context(
                    active_model=budget_constraint._name,
                    active_id=budget_constraint.id,
                    doclines=doclines,
                )
                .sudo()
                .run()
            )
            if msg_error:
                all_msg_error += "\n".join(msg_error)
        if all_msg_error:
            raise UserError(_(all_msg_error))
        return True

    @api.model
    def check_budget(self, doclines, doc_type="account"):
        """Create budget commit for each docline"""
        self = self.sudo()
        budget_constraints = self._get_budget_constraint()
        # Find active budget.period based on latest doclines date_commit
        date_commit = doclines.filtered("date_commit").mapped("date_commit")
        if not date_commit:
            return super().check_budget(doclines, doc_type)
        date_commit = max(date_commit)
        budget_period = self._get_eligible_budget_period(date_commit, doc_type=doc_type)
        if doclines and budget_constraints and budget_period:
            self.check_budget_constraint(budget_constraints, doclines)
        return super().check_budget(doclines, doc_type)
