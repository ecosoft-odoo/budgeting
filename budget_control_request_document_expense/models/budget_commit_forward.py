# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BudgetCommitForward(models.Model):
    _inherit = "budget.commit.forward"

    def _get_model_request_line(self):
        res = super()._get_model_request_line()
        res.append("request.document.expense.line")
        return res

    def _prepare_vals_forward(self, docs, res_model):
        value_dict = super()._prepare_vals_forward(docs, res_model)
        if (
            res_model == "request.document"
            and docs._name == "request.document.expense.line"
        ):
            pass
            # for val in value_dict:
            #     val["res_model"] = "request.document.expense.line"
        return value_dict


class BudgetCommitForwardLine(models.Model):
    _inherit = "budget.commit.forward.line"

    document_id = fields.Reference(
        selection_add=[("request.document.expense.line", "Request Document")],
        ondelete={"request.document.expense.line": "cascade"},
    )
    document_number = fields.Reference(
        selection_add=[("request.document", "Request")],
        ondelete={"request.document": "cascade"},
    )
