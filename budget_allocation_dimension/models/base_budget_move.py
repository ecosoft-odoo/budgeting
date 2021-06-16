# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BaseBudgetMove(models.AbstractModel):
    _name = "base.budget.move"
    _inherit = ["analytic.dimension.line", "base.budget.move"]
    _analytic_tag_field_name = "analytic_tag_ids"

    def _get_dimension_fields(self):
        if self.env.context.get("update_custom_fields"):
            return []  # Avoid to report these columns when not yet created
        return [
            x for x in self.fields_get().keys() if x.startswith("x_dimension_")
        ]

    def _get_fields_read_group(self):
        fields = super()._get_fields_read_group()
        fields.extend(self._get_dimension_fields())
        return fields

    def _get_groupby_read_group(self):
        groupby = super()._get_fields_read_group()
        groupby.extend(self._get_dimension_fields())
        return groupby

    def _get_ba_line_group(self, budget_allocation_lines, obj_group):
        ba_line_group = super()._get_ba_line_group(
            budget_allocation_lines, obj_group
        )
        dimensions = self._get_dimension_fields()
        for x in dimensions:
            # check case no dimension
            obj_group_id = obj_group[x] and obj_group[x][0] or False
            ba_line_group = ba_line_group.filtered(
                lambda l: l[x].id == obj_group_id
            )
        return ba_line_group

    def _get_move_commit(self, obj, obj_group):
        move_commit = super()._get_move_commit(obj, obj_group)
        dimensions = self._get_dimension_fields()
        for x in dimensions:
            # check case no dimension
            obj_group_id = obj_group[x] and obj_group[x][0] or False
            move_commit = move_commit.filtered(
                lambda l: l[x].id == obj_group_id
            )
        return move_commit


class BudgetDoclineMixin(models.AbstractModel):
    _inherit = "budget.docline.mixin"

    analytic_tag_all = fields.Many2many(
        comodel_name="account.analytic.tag",
        compute="_compute_analytic_tag_all",
        compute_sudo=True,
    )

    def _get_dimension_fields(self):
        if self.env.context.get("update_custom_fields"):
            return []  # Avoid to report these columns when not yet created
        return [
            x for x in self.fields_get().keys() if x.startswith("x_dimension_")
        ]

    def _compute_analytic_tag_all(self):
        for doc in self:
            dimension_fields = doc._get_dimension_fields()
            analytic_tag_ids = doc[
                doc._budget_analytic_field
            ].allocation_line_ids.mapped(doc._analytic_tag_field_name)
            doc.analytic_tag_all = analytic_tag_ids
            if (
                len(analytic_tag_ids) != len(dimension_fields)
                and doc.analytic_tag_ids
            ):
                continue
            doc.analytic_tag_ids = (
                len(analytic_tag_ids) == len(dimension_fields)
                and analytic_tag_ids
                or False
            )
