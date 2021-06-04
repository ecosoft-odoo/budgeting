# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


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
        return ba_line_group.filtered(
            lambda l: l.fund_id.id == obj_group["fund_id"][0]
        )

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
    )
    fund_all = fields.Many2many(
        comodel_name="budget.source.fund",
        compute="_compute_fund_all",
        compute_sudo=True,
    )

    def _compute_fund_all(self):
        for doc in self:
            fund_ids = doc[
                doc._budget_analytic_field
            ].allocation_line_ids.mapped("fund_id")
            doc.fund_all = fund_ids
            if len(fund_ids) > 1 and doc.fund_id and doc.fund_id in fund_ids:
                continue
            doc.fund_id = len(fund_ids) == 1 and fund_ids.id or False

    def _update_budget_commitment(self, budget_vals, reverse=False):
        budget_vals = super()._update_budget_commitment(
            budget_vals, reverse=reverse
        )
        budget_vals["fund_id"] = self.fund_id.id
        budget_vals["fund_group_id"] = self.fund_id.fund_group_id.id
        return budget_vals
