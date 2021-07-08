# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class BudgetPeriod(models.Model):
    _inherit = "budget.period"

    use_budget_constraint = fields.Boolean(
        string="Use Budget Constraint",
        default=False,
    )

    def _get_budget_constraint(self):
        return self.env["budget.constraint"].search([], order="sequence")

    @api.model
    def check_budget_constraint(self, doclines, doc_type):
        # Find active budget.period based on latest doclines date_commit
        date_commit = doclines.filtered("date_commit").mapped("date_commit")
        if not date_commit:
            return
        date_commit = max(date_commit)
        budget_period = self._get_eligible_budget_period(
            date_commit, doc_type=doc_type
        )
        if not (budget_period and budget_period.use_budget_constraint):
            return
        budget_constraints = self._get_budget_constraint()
        message = []
        for budget_constraint in budget_constraints:
            result = (
                budget_constraint.server_action_id.with_context(
                    active_model=budget_constraint._name,
                    active_id=budget_constraint.id,
                    doclines=doclines,
                )
                .sudo()
                .run()
            )
            if result:
                message.extend(result)
        return message

    @api.model
    def check_budget(self, doclines, doc_type="account"):
        super().check_budget(doclines, doc_type)
        message = self.check_budget_constraint(doclines, doc_type)
        if message:
            raise UserError(_("\n".join(message)))
