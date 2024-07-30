# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BudgetCommitForward(models.Model):
    _inherit = "budget.commit.forward"

    advance = fields.Boolean(
        default=True,
        help="If checked, click review budget commitment will pull advance commitment",
    )
    forward_advance_ids = fields.One2many(
        comodel_name="budget.commit.forward.line",
        inverse_name="forward_id",
        string="Fwd Advances",
        domain=[("res_model", "=", "hr.expense.advance")],
    )

    def _get_budget_docline_model(self):
        res = super()._get_budget_docline_model()
        if self.advance:
            res.append("hr.expense.advance")
        return res

    def _get_document_number(self, doc):
        if doc._name == "hr.expense.advance":
            return f"{doc.sheet_id._name},{doc.sheet_id.id}"
        return super()._get_document_number(doc)

    def _get_name_model(self, res_model, need_replace=False):
        if res_model == "hr.expense.advance":
            if need_replace:
                return "hr_expense"
            return "hr.expense"
        return super()._get_name_model(res_model, need_replace)

    def _get_base_from_extension(self, res_model):
        """For module extension"""
        if res_model != "hr.expense.advance":
            return super()._get_base_from_extension(res_model)
        query_from = "JOIN hr_expense_sheet sheet ON sheet.id = a.sheet_id"
        return query_from

    def _get_base_domain_extension(self, res_model):
        """For module extension"""
        if res_model not in ["hr.expense.advance", "hr.expense"]:
            return super()._get_base_domain_extension(res_model)

        query_where = " AND a.state != 'cancel'"
        # Special case, model = hr.expense with advance
        if res_model == "hr.expense.advance":
            query_where += " AND a.advance = True AND sheet.clearing_residual > 0.0"
        else:
            query_where += " AND a.advance = False"
        return query_where


class BudgetCommitForwardLine(models.Model):
    _inherit = "budget.commit.forward.line"

    res_model = fields.Selection(
        selection_add=[("hr.expense.advance", "Advance")],
        ondelete={"hr.expense.advance": "cascade"},
    )
