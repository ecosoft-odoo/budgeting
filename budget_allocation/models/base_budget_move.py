# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from psycopg2 import sql

from odoo import _, api, fields, models
from odoo.tools import float_compare


class BaseBudgetMove(models.AbstractModel):
    _name = "base.budget.move"
    _inherit = ["analytic.dimension.line", "base.budget.move"]
    _analytic_tag_field_name = "analytic_tag_ids"

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

    def _get_where_commitment(self, docline):
        fund_domain = (
            "fund_id = {}".format(docline.fund_id.id)
            if docline.fund_id
            else "fund_id is null"
        )
        dimensions = docline._get_dimension_fields()
        analytic_tag_domain = [
            "({0} {1} {2} or {0} = 999999990)".format(
                dimension,
                docline[dimension] and "=" or "is",
                docline[dimension] and docline[dimension].id or "null",
            )
            for dimension in dimensions
        ]
        analytic_tag_domain = " and ".join(analytic_tag_domain)
        where_query = (
            "analytic_account_id = {analytic} and active = True"
            " and {fund_domain} and {analytic_tag_domain}".format(
                analytic=docline[docline._budget_analytic_field].id,
                fund_domain=fund_domain,
                analytic_tag_domain=analytic_tag_domain,
            )
        )
        return where_query

    def _get_budget_source_fund_report(self):
        # TODO: Change it support OU
        # return self.env["budget.source.fund.report"].with_context(force_all_ou=1)._table_query
        return self.env["budget.source.fund.report"]

    def _get_query_dict(self, docline):
        self._cr.execute(
            sql.SQL(
                """
            SELECT * FROM ({monitoring}) report
            WHERE {where_query_commitment}""".format(
                    monitoring=self._get_budget_source_fund_report()._table_query,
                    where_query_commitment=self._get_where_commitment(docline),
                )
            )
        )
        return self.env.cr.dictfetchall()

    @api.model
    def check_budget_allocation_limit(self, doclines):
        """
        Check amount with budget allocation, based on budget source fund report.

        1. Check analytic account from commitment.
        2. Find budget allocation line from condition with monitoring.
        3. Calculate released amount on budget allocation (2) - commitment,
        ensuring it is not negative (1).

        Note: This is a base function that can be used by server actions or installed
        as part of the `budget_constraint` module.

        Example usage:

        Budget allocation has allocation:
            Allocation Line | Analytic Account | Fund  | Tags | Allocated | ...
            --------------------------------------------------------------
            1               |               A  | Fund1 | Tag1 |     100.0 | ...
            2               |               A  | Fund2 | Tag2 |     100.0 | ...

        Condition constraint (e.g. invoice lines)
            - User can use:
            Document | Line | Analytic Account | Fund  | Tags | Amount |
            -----------------------------------------------------------------------
            INV001   |    1 |             A    | Fund1 | Tag1 | 130.0  | >>> Error (-30)
            -----------------------------------------------------------------------
            INV002   |    1 |             A    | Fund1 |      | 10.0 | >>> Not allocated
            INV002   |    1 |             A    | Fund1 | Tag1 | 10.0 | >>> balance 90
            INV002   |    2 |             A    | Fund1 | Tag1 | 60.0 | >>> balance 30
            ----------------------------Confirm----------------------------
            INV003   |    1 |             A    | Fund1 | Tag1 | 10.0 | >>> balance 20
            INV003   |    2 |             A    | Fund1 | Tag1 | 60.0 | >>> Error (-40)
            ---------------------------------------------------------------
            INV004   |    1 |             A    | Fund2 | Tag1 |120.0 | >>> Not allocated
            INV004   |    1 |             A    | Fund2 | Tag2 |120.0 | >>> Error (-20)
        """
        # Base on budget source fund monitoring
        errors = []
        for docline in doclines:
            if not docline[docline._budget_analytic_field]:
                continue
            name = docline.name
            fund_name = docline.fund_id.name
            tag_name = ", ".join(docline.analytic_tag_ids.mapped("name"))
            query_dict = self._get_query_dict(docline)
            if not any(x["amount_type"] == "1_budget" for x in query_dict):
                errors.append(
                    _("{} & {} & {} is not allocated on budget allocation").format(
                        name, fund_name, tag_name or "False"
                    )
                )
                continue
            total_spend = sum(
                x["amount"] for x in query_dict if isinstance(x["amount"], float)
            )
            # Check that amount after commit is more than 0.0
            prec_digits = self.env.user.company_id.currency_id.decimal_places
            if float_compare(total_spend, 0.0, precision_digits=prec_digits) == -1:
                errors.append(
                    _(
                        "{} & {} & {} spend amount over budget allocation limit {:,.2f}"
                    ).format(name, fund_name, tag_name or "False", total_spend)
                )
        return errors


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
        compute="_compute_allocation_line_all",
    )
    analytic_tag_all = fields.Many2many(
        comodel_name="account.analytic.tag",
        compute="_compute_allocation_line_all",
    )

    def _get_dimension_fields(self):
        if self.env.context.get("update_custom_fields"):
            return []  # Avoid to report these columns when not yet created
        return [x for x in self.fields_get().keys() if x.startswith("x_dimension_")]

    @api.onchange("fund_all")
    def _onchange_fund_all(self):
        for rec in self:
            rec.fund_id = rec.fund_all._origin.id if len(rec.fund_all) == 1 else False

    @api.depends(
        lambda self: (self._budget_analytic_field,)
        if self._budget_analytic_field
        else ()
    )
    def _compute_allocation_line_all(self):
        for rec in self:
            allocation_lines = rec[rec._budget_analytic_field].allocation_line_ids
            rec.fund_all = allocation_lines.mapped("fund_id")
            rec.analytic_tag_all = allocation_lines.mapped("analytic_tag_ids")


class BudgetDoclineMixin(models.AbstractModel):
    _inherit = "budget.docline.mixin"

    def _update_budget_commitment(self, budget_vals, reverse=False):
        budget_vals = super()._update_budget_commitment(budget_vals, reverse=reverse)
        budget_vals["fund_id"] = self.fund_id.id
        budget_vals["fund_group_id"] = self.fund_id.fund_group_id.id
        return budget_vals
