# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BudgetCommitForward(models.Model):
    _inherit = "budget.commit.forward"

    request = fields.Boolean(
        default=True,
        help="If checked, click review budget commitment will pull request commitment",
    )
    forward_request_ids = fields.One2many(
        comodel_name="budget.commit.forward.line",
        inverse_name="forward_id",
        string="Request",
        domain=[("res_model", "=", "request.document")],
    )

    def _get_budget_docline_model(self):
        res = super()._get_budget_docline_model()
        if self.request:
            res.append("request.document")
        return res

    def _get_document_number(self, doc):
        if doc._name in self._get_model_request_line():
            return f"{doc.document_id._name},{doc.document_id.id}"
        return super()._get_document_number(doc)

    def _get_model_request_line(self):
        return []

    def get_budget_commit_forward(self, res_model):
        if res_model == "request.document":
            self = self.sudo()
            Line = self.env["budget.commit.forward.line"]
            for rec in self:
                request_docs = rec._get_request_commit_docline(res_model)
                for docs in request_docs:
                    vals = rec._prepare_vals_forward(docs, res_model)
                    Line.create(vals)
            return True
        return super().get_budget_commit_forward(res_model)

    def _get_request_commit_docline(self, res_model):
        model_obj = []
        for model_line in self._get_model_request_line():
            domain = self._get_base_domain()
            domain.extend(
                [
                    ("analytic_account_id", "!=", False),
                    ("document_id.state", "=", "approve"),
                ]
            )
            request_line = self.env[model_line].search(domain)
            if request_line:
                model_obj.append(request_line)
        return model_obj


class BudgetCommitForwardLine(models.Model):
    _inherit = "budget.commit.forward.line"

    res_model = fields.Selection(
        selection_add=[("request.document", "Request Document")],
        ondelete={"request.document": "cascade"},
    )
