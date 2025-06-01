# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


# pylint: disable=consider-merging-classes-inherited
class RequestDocument(models.Model):
    _inherit = "request.document"

    move_ids = fields.One2many(
        comodel_name="account.move",
        inverse_name="request_document_id",
    )

    def _get_origin_lines(self):
        vals = super()._get_origin_lines()
        vals["tester"] = "move_ids.invoice_line_ids"
        return vals

    def _get_data_amount(self, request_line):
        if request_line._name == "account.move.line":  # Test
            data_amount = []
            for doc_line in request_line:
                if doc_line.move_id.move_type == "entry":
                    total_amount = doc_line.amount_currency
                else:
                    sign = -1 if doc_line.is_refund else 1
                    discount = (
                        (100 - doc_line.discount) / 100 if doc_line.discount else 1
                    )
                    total_amount = (
                        sign * doc_line.price_unit * doc_line.quantity * discount
                    )
                data_amount.append({doc_line.id: total_amount})
            return data_amount
        return super()._get_data_amount(request_line)

    def uncommit_request_budget(self, request_line):
        """Process uncommit budget, when document is changed state"""
        res = super().uncommit_request_budget(request_line)
        budget_move = request_line[request_line._budget_move_field]
        # Move with state posted will auto close budget
        if (
            request_line._name == "account.move.line"
            and budget_move
            and request_line[request_line._doc_rel].state == "posted"
        ):
            budget_moves = self.close_budget_move()
            return budget_moves
        return res

    def _create_tester(self):
        """Process that we need, when click action_process_document"""
        res = super()._create_tester()
        self.move_ids.action_post()
        return res


# pylint: disable=consider-merging-classes-inherited
class AccountMove(models.Model):
    _inherit = "account.move"

    request_document_id = fields.Many2one(
        comodel_name="request.document",
        ondelete="cascade",
    )

    def write(self, vals):
        """Uncommit budget for source request document."""
        res = super().write(vals)
        if vals.get("state") in ("posted", "cancel", "draft"):
            self.mapped("request_document_id").recompute_budget_move()
        return res


# pylint: disable=consider-merging-classes-inherited
class BudgetDoclineMixin(models.AbstractModel):
    _inherit = "budget.docline.mixin"

    def _init_docline_budget_vals(self, budget_vals, analytic_id):
        """Use standard budget move but we need commit in request"""
        budget_vals = super()._init_docline_budget_vals(budget_vals, analytic_id)
        if (
            self.env.context.get("alt_budget_move_model") == "request.budget.move"
            and self._name == "account.move.line"
        ):
            budget_vals.pop("move_line_id")  # Delete expense reference
            budget_vals["request_document_id"] = self[
                self._doc_rel
            ].request_document_id.id
        return budget_vals
