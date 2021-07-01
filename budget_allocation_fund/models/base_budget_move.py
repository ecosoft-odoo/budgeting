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

    def _get_fields_read_group(self):
        fields = super()._get_fields_read_group()
        fields.append("fund_id")
        return fields

    def _get_groupby_read_group(self):
        groupby = super()._get_fields_read_group()
        groupby.append("fund_id")
        return groupby

    def _get_ba_line_group(self, budget_allocation_lines, obj_group):
        ba_line_group = super()._get_ba_line_group(
            budget_allocation_lines, obj_group
        )
        # check case no fund
        obj_group = obj_group["fund_id"] and obj_group["fund_id"][0] or False
        return ba_line_group.filtered(lambda l: l.fund_id.id == obj_group)

    def _get_move_commit(self, obj, obj_group):
        move_commit = super()._get_move_commit(obj, obj_group)
        return move_commit.filtered(
            lambda l: l.fund_id.id == obj_group["fund_id"][0]
        )


class BudgetDoclineMixin(models.AbstractModel):
    _inherit = "budget.docline.mixin"

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
        for doc in self:
            doc.fund_all = doc[
                doc._budget_analytic_field
            ].allocation_line_ids.mapped("fund_id")

    def _update_budget_commitment(self, budget_vals, reverse=False):
        budget_vals = super()._update_budget_commitment(
            budget_vals, reverse=reverse
        )
        budget_vals["fund_id"] = self.fund_id.id
        budget_vals["fund_group_id"] = self.fund_id.fund_group_id.id
        return budget_vals
