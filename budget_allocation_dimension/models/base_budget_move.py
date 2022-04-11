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

    def _get_condition_skip_dimension(self):
        """
        This function will check state 2 module
            1. budget_source_fund
            2. budget_allocation_dimension_fund

        ============ budget.monitor.report ============
        - Not install module `budget_source_fund` -> query dimension

        ============ source.fund.monitor.report ============
        - Install module `budget_source_fund`,
          Not install module `budget_allocation_dimension_fund` -> skip dimension
        - Install module `budget_source_fund`,
          install module `budget_allocation_dimension_fund` -> query dimension
        """
        dimension_fund = (
            self.env["ir.module.module"]
            .sudo()
            .search(
                [
                    ("name", "=", "budget_allocation_dimension_fund"),
                    ("state", "!=", "installed"),
                ],
                limit=1,
            )
        )
        # Skip query dimension
        if (
            self.env["budget.monitor.report"].is_budget_source_fund_installed()
            and dimension_fund
        ):
            return True
        return False

    def _get_where_commitment(self, docline):
        where_query = super()._get_where_commitment(docline)
        skip_query_dimension = self._get_condition_skip_dimension()
        if skip_query_dimension:
            return where_query
        dimensions = docline._get_dimension_fields()
        where_dimensions = [
            "({0} {1} {2} or {0} = 999999990)".format(
                x,
                docline[x] and "=" or "is",
                docline[x] and docline[x].id or "null",
            )
            for x in dimensions
        ]
        where_dimensions = " and ".join(where_dimensions)
        return (
            where_dimensions
            and " and ".join([where_query, where_dimensions])
            or where_query
        )


class BudgetDoclineMixinBase(models.AbstractModel):
    _inherit = "budget.docline.mixin.base"

    analytic_tag_all = fields.Many2many(
        comodel_name="account.analytic.tag",
        compute="_compute_analytic_tag_all",
        compute_sudo=True,
    )

    @api.onchange("analytic_tag_all")
    def _onchange_analytic_tag_all(self):
        dimension_fields = self._get_dimension_fields()
        analytic_tag_ids = self[
            self._budget_analytic_field
        ].allocation_line_ids.mapped("analytic_tag_ids")
        if (
            len(analytic_tag_ids) != len(dimension_fields)
            and self[self._analytic_tag_field_name]
        ):
            return
        self[self._analytic_tag_field_name] = (
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
            ].allocation_line_ids.mapped("analytic_tag_ids")
            doc.analytic_tag_all = analytic_tag_ids
