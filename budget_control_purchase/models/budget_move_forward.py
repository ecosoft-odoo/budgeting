# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class BudgetMoveForward(models.Model):
    _inherit = "budget.move.forward"

    forward_purchase_ids = fields.One2many(
        comodel_name="budget.move.forward.line",
        inverse_name="forward_id",
        string="Purchase Orders",
        domain=[("res_model", "=", "purchase.order.line")],
    )

    def _filter_current_move(self, doc):
        if doc._name == "purchase.order.line":
            return doc.budget_move_ids.filtered(
                lambda l: l.analytic_account_id == doc.account_analytic_id
            )
        return super()._filter_current_move(doc)

    def _get_document_number(self, doc, model):
        if model == "purchase.order.line":
            return doc.order_id.name
        return super()._get_document_number(doc, model)

    def _get_domain_search(self, model):
        """ Filter Purchase used analytic account"""
        domain_search = super()._get_domain_search(model)
        if model == "purchase.order.line":
            domain_search.extend(
                [
                    ("account_analytic_id", "!=", False),
                    ("state", "!=", "cancel"),
                ]
            )
        return domain_search


class BudgetMoveForwardLine(models.Model):
    _inherit = "budget.move.forward.line"

    res_model = fields.Selection(
        selection_add=[("purchase.order.line", "Purchase")],
        ondelete={"purchase.order.line": "cascade"},
    )
    document_id = fields.Reference(
        selection_add=[("purchase.order.line", "Purchase")],
        ondelete={"purchase.order.line": "cascade"},
    )
