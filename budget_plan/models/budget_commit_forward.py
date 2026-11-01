# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from collections import defaultdict

from odoo import models
from odoo.exceptions import UserError


class BudgetCommitForward(models.Model):
    _inherit = "budget.commit.forward"

    def action_budget_commit_forward(self):
        res = super().action_budget_commit_forward()
        self._check_forward_allocation()
        return res

    def _check_forward_allocation(self):
        """The commitments carried forward fit the allocations by dimension of
        the target period, when it controls them."""
        Detail = self.env["budget.plan.line.detail"]
        self.env.flush_all()
        messages = []
        for forward in self.sudo():
            period = forward.to_budget_period_id
            if not (period.control_budget and period.control_allocation):
                continue
            # The carried commitments, by budget move model
            moves_by_model = defaultdict(list)
            for line in forward.forward_line_ids:
                docline = line.document_id
                moves = docline[docline._budget_field()].filtered(
                    lambda move, forward=forward: (
                        move.fwd_commit and move.date == forward.to_date_commit
                    )
                )
                moves_by_model[moves._name] += moves.ids
            for model, move_ids in moves_by_model.items():
                messages += Detail._check_budget_allocation(
                    period, self.env[model].browse(move_ids)
                )
        if messages:
            raise UserError("\n".join(dict.fromkeys(messages)))
