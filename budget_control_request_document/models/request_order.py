# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class RequestOrder(models.Model):
    _inherit = "request.order"

    budget_move_ids = fields.One2many(
        comodel_name="request.budget.move",
        inverse_name="request_id",
    )

    @api.constrains("line_ids")
    def recompute_budget_move(self):
        self.mapped("line_ids").recompute_budget_move()

    def close_budget_move(self):
        budget_moves = self.mapped("line_ids").close_budget_move()
        return budget_moves

    def _clear_date_commit(self, doclines):
        clear_date_commit = {"date_commit": False}
        for line in doclines:
            request_line = line._get_lines_request()
            if request_line:
                request_line.write(clear_date_commit)

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
            else:
                doclines = doclines.with_context(
                    force_commit=True,
                    alt_budget_move_model="request.budget.move",
                    alt_budget_move_field="budget_move_ids",
                )
            doclines.recompute_budget_move()
        return res

    def action_approve(self):
        res = super().action_approve()
        BudgetPeriod = self.env["budget.period"]
        for doc in self:
            for line in doc.line_ids:
                request_line = line._get_lines_request()
                if request_line:
                    BudgetPeriod.check_budget(request_line, doc_type="request")
                    # Add amount each line in JSON,
                    # for case change amount after approved
                    line.line_data_amount = line._get_data_amount(request_line)
        return res

    def action_submit(self):
        res = super().action_submit()
        BudgetPeriod = self.env["budget.period"]
        for doc in self:
            for line in doc.line_ids:
                request_line = line._get_lines_request()
                if request_line:
                    BudgetPeriod.check_budget_precommit(
                        request_line, doc_type="request"
                    )
        return res

    def clear_data_amount(self):
        return self.mapped("line_ids").write({"line_data_amount": False})

    def action_cancel(self):
        self.clear_data_amount()
        return super().action_cancel()

    def action_draft(self):
        self.clear_data_amount()
        return super().action_draft()
