# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class BudgetPlan(models.Model):
    _inherit = "budget.plan"

    revision_number = fields.Integer(readonly=True)

    def create_revision(self):
        budget_controls = self.budget_control_ids
        control_state = set(budget_controls.mapped("state"))
        if len(control_state) != 1 or "cancel" not in control_state:
            raise UserError(
                _(
                    "Can not revision. All budget control have to state 'cancel'"
                )
            )
        action = budget_controls.create_revision()
        self.action_draft()
        self.revision_number += 1
        return action
