# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class RequestRequest(models.Model):
    _inherit = "request.request"

    budget_move_ids = fields.One2many(
        comodel_name="request.budget.move",
        inverse_name="request_id",
    )

    @api.constrains("line_ids")
    def recompute_budget_move(self):
        self.mapped("line_ids").recompute_budget_move()

    def close_budget_move(self):
        self.mapped("line_ids").close_budget_move()

    def _clear_date_commit(self, doclines):
        clear_date_commit = {"date_commit": False}
        for line in doclines:
            request_line = line._get_lines_request()
            if request_line:
                line.mapped(request_line).write(clear_date_commit)

    def write(self, vals):
        """
        Uncommit budget when the state is "approve" or cancel/draft the document.
        When the document is cancelled or drafted, delete all budget commitments.
        """
        res = super().write(vals)
        if vals.get("state") in ("approve", "cancel", "draft"):
            doclines = self.mapped("line_ids")
            if vals.get("state") in ("cancel", "draft"):
                self._clear_date_commit(doclines)
            doclines.recompute_budget_move()
        return res

    def action_approve(self):
        res = super().action_approve()
        self.flush()
        BudgetPeriod = self.env["budget.period"]
        for doc in self:
            for line in doc.line_ids:
                request_line = line._get_lines_request()
                if request_line:
                    BudgetPeriod.check_budget(
                        line.mapped(request_line), doc_type="request"
                    )
        return res

    def action_submit(self):
        res = super().action_submit()
        BudgetPeriod = self.env["budget.period"]
        for doc in self:
            for line in doc.line_ids:
                request_line = line._get_lines_request()
                if request_line:
                    BudgetPeriod.check_budget_precommit(
                        line.mapped(request_line), doc_type="request"
                    )
        return res
