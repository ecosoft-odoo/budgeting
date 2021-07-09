# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


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

    def _where_query_source_fund(self, docline):
        where_query = super()._where_query_source_fund(docline)
        dimensions = docline._get_dimension_fields()
        where_dimensions = [
            "{} {} {}".format(
                x,
                docline[x] and "=" or "is",
                docline[x] and docline[x].id or "null",
            )
            for x in dimensions
        ]
        where_dimensions = " and ".join(where_dimensions)
        return " and ".join([where_query, where_dimensions])


class BudgetDoclineMixin(models.AbstractModel):
    _inherit = "budget.docline.mixin"

    analytic_tag_all = fields.Many2many(
        comodel_name="account.analytic.tag",
        compute="_compute_analytic_tag_all",
        compute_sudo=True,
    )

    @api.onchange("analytic_tag_all")
    def _onchange_analytic_tag_all(self):
        for doc in self:
            dimension_fields = doc._get_dimension_fields()
            analytic_tag_ids = doc[
                doc._budget_analytic_field
            ].allocation_line_ids.mapped(doc._analytic_tag_field_name)
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

    def _get_dimension_fields(self):
        if self.env.context.get("update_custom_fields"):
            return []  # Avoid to report these columns when not yet created
        return [
            x for x in self.fields_get().keys() if x.startswith("x_dimension_")
        ]

    @api.depends(
        lambda self: (self._budget_analytic_field,)
        if self._budget_analytic_field
        else ()
    )
    def _compute_analytic_tag_all(self):
        for doc in self:
            analytic_tag_ids = doc[
                doc._budget_analytic_field
            ].allocation_line_ids.mapped(doc._analytic_tag_field_name)
            doc.analytic_tag_all = analytic_tag_ids
