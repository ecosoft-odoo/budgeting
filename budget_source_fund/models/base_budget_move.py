# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class BaseBudgetMove(models.AbstractModel):
    _inherit = "base.budget.move"

    fund_id = fields.Many2one(
        comodel_name="budget.source.fund",
        string="Fund",
        index=True,
    )
    fund_group_id = fields.Many2one(
        comodel_name="budget.source.fund.group",
        string="Fund Group",
        index=True,
    )

    def _where_query_source_fund(self, docline):
        where_query = super()._where_query_source_fund(docline)
        where_fund = "fund_id {} {}".format(
            docline.fund_id and "=" or "is", docline.fund_id.id or "null"
        )
        return " and ".join([where_query, where_fund])


class BudgetDoclineMixinBase(models.AbstractModel):
    _inherit = "budget.docline.mixin.base"

    fund_id = fields.Many2one(
        comodel_name="budget.source.fund",
        index=True,
        ondelete="restrict",
        domain="[('id', 'in', fund_all)]",
    )
    fund_all = fields.Many2many(
        comodel_name="budget.source.fund",
        compute="_compute_fund_all",
        compute_sudo=True,
    )

    @api.onchange("fund_all")
    def _onchange_fund_all(self):
        for rec in self:
            rec.fund_id = (
                rec.fund_all._origin.id if len(rec.fund_all) == 1 else False
            )

    @api.depends(
        lambda self: (self._budget_analytic_field,)
        if self._budget_analytic_field
        else ()
    )
    def _compute_fund_all(self):
        SourceFund = self.env["budget.source.fund"]
        source_fund_all = SourceFund.search([])
        for doc in self:
            budget_analytic_fields = doc[doc._budget_analytic_field]
            field_allocation_line = budget_analytic_fields._fields.get(
                "allocation_line_ids"
            )
            # show all fund, when not install 'budget_allocation_fund' module
            doc.fund_all = (
                field_allocation_line
                and budget_analytic_fields.allocation_line_ids.mapped(
                    "fund_id"
                )
                or source_fund_all
            )


class BudgetDoclineMixin(models.AbstractModel):
    _inherit = "budget.docline.mixin"

    def _update_budget_commitment(self, budget_vals, reverse=False):
        budget_vals = super()._update_budget_commitment(
            budget_vals, reverse=reverse
        )
        budget_vals["fund_id"] = self.fund_id.id
        budget_vals["fund_group_id"] = self.fund_id.fund_group_id.id
        return budget_vals
