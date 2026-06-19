# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BudgetCommitForward(models.Model):
    _inherit = "budget.commit.forward"

    stock = fields.Boolean(
        default=True,
        help="If checked, click review budget commitment will pull stock commitment",
    )
    forward_stock_ids = fields.One2many(
        comodel_name="budget.commit.forward.line",
        inverse_name="forward_id",
        string="Stock Moves",
        domain=[("res_model", "=", "stock.move")],
    )

    def _get_budget_docline_model(self):
        res = super()._get_budget_docline_model()
        if self.stock:
            res.append("stock.move")
        return res

    def _get_document_number(self, doc):
        if doc._name == "stock.move":
            return f"{doc.picking_id._name},{doc.picking_id.id}"
        return super()._get_document_number(doc)

    def _get_base_domain_extension(self, res_model):
        """For module extension"""
        if res_model == "stock.move":
            return " AND a.state NOT IN ('cancel', 'draft')"
        return super()._get_base_domain_extension(res_model)


class BudgetCommitForwardLine(models.Model):
    _inherit = "budget.commit.forward.line"

    res_model = fields.Selection(
        selection_add=[("stock.move", "Stock Move")],
        ondelete={"stock.move": "cascade"},
    )
    document_id = fields.Reference(
        selection_add=[("stock.move", "Stock Move")],
        ondelete={"stock.move": "cascade"},
    )
    document_number = fields.Reference(
        selection_add=[("stock.picking", "Stock Picking")],
        ondelete={"stock.picking": "cascade"},
    )
