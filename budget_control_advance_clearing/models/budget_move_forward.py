# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class BudgetMoveForward(models.Model):
    _inherit = "budget.move.forward"

    forward_advance_ids = fields.One2many(
        comodel_name="budget.move.forward.line",
        inverse_name="forward_id",
        string="Advance / Clearing",
        domain=[("res_model", "=", "hr.expense.advance")],
    )

    def _get_document_number(self, doc):
        if doc._name == "hr.expense.advance":
            return doc.name
        return super()._get_document_number(doc)

    def _prepare_vals_forward(self, docs, model):
        value_dict = super()._prepare_vals_forward(docs, model)
        if model == "hr.expense" and self._context.get("advance", False):
            for val in value_dict:
                val["res_model"] = "hr.expense.advance"
        return value_dict

    def _get_domain_unlink(self, model):
        if model == "hr.expense" and self._context.get("advance", False):
            return [
                ("forward_id", "=", self.id),
                ("res_model", "=", "hr.expense.advance"),
            ]
        return super()._get_domain_unlink(model)

    def _get_domain_search(self, model):
        """ Filter case expense and advance """
        domain_search = super()._get_domain_search(model)
        if model == "hr.expense":
            domain_search.extend(
                [
                    ("advance", "=", self._context.get("advance", False)),
                ]
            )
        return domain_search


class BudgetMoveForwardLine(models.Model):
    _inherit = "budget.move.forward.line"

    res_model = fields.Selection(
        selection_add=[("hr.expense.advance", "Advance")],
        ondelete={"hr.expense.advance": "cascade"},
    )
    document_id = fields.Reference(
        selection_add=[("hr.expense", "Advance")],
        ondelete={"hr.expense": "cascade"},
    )
