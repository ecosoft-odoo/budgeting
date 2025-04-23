# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.tools import SQL, float_compare


class BaseBudgetMove(models.AbstractModel):
    _name = "base.budget.move"
    _inherit = ["analytic.dimension.line", "base.budget.move"]
    _analytic_tag_field_name = "analytic_tag_ids"

    analytic_tag_ids = fields.Many2many(
        comodel_name="account.analytic.tag",
        string="Analytic Tags",
    )
    fund_id = fields.Many2one(
        comodel_name="budget.source.fund",
        index=True,
    )
    fund_group_id = fields.Many2one(
        comodel_name="budget.source.fund.group",
        index=True,
    )

    def _get_where_commitment(self, docline):
        fund_domain = (
            f"fund_id = {docline.fund_id.id}" if docline.fund_id else "fund_id is null"
        )
        dimensions = docline._get_dimension_fields()
        analytic_tag_domain = [
            "({} {} {})".format(
                dimension,
                docline[dimension] and "=" or "is",
                docline[dimension] and docline[dimension].id or "null",
            )
            for dimension in dimensions
        ]
        analytics = docline._convert_analytics()
        analytic_tag_domain = " and ".join(analytic_tag_domain)
        where_query = (
            "analytic_account_id = {analytic} and active = True"
            " and {fund_domain} {analytic_tag_domain}".format(
                analytic=analytics.id,
                fund_domain=fund_domain,
                analytic_tag_domain=f"and {analytic_tag_domain}"
                if analytic_tag_domain
                else "",
            )
        )
        return where_query

    def _get_budget_source_fund_report(self):
        return self.env["budget.source.fund.report"]

    def _get_query_dict(self, docline):
        self.env.cr.execute(
            SQL(
                f"""
                    SELECT amount, amount_type, budget_period_id
                    FROM (%s) report
                    WHERE {self._get_where_commitment(docline)}
                """,
                SQL(self._get_budget_source_fund_report()._table_query),
            )
        )
        dict_data = self.env.cr.dictfetchall()
        return dict_data

    def _map_commit_dates_to_periods(self, dates_to_lookup):
        periods_map = {}
        if dates_to_lookup:
            min_date = min(dates_to_lookup)
            max_date = max(dates_to_lookup)
            relevant_periods = self.env["budget.period"].search(
                [
                    ("bm_date_from", "<=", max_date),
                    ("bm_date_to", ">=", min_date),
                ]
            )
            for date_to_map in dates_to_lookup:
                matching = relevant_periods.filtered(
                    lambda p, date_to_map=date_to_map: p.bm_date_from
                    <= date_to_map
                    <= p.bm_date_to
                )
                periods_map[date_to_map] = matching.id if len(matching) == 1 else False
        return periods_map

    @api.model
    def check_budget_detail_limit(self, doclines):
        """
        Check amount with budget detail, based on budget source fund report.

        1. Check analytic account from commitment.
        2. Find budget detail from condition with monitoring.
        3. Calculate released amount on budget detail (2) - commitment,
        ensuring it is not negative (1).

        Note: This is a base function that can be used by server actions or installed
        as part of the `budget_constraint` module.

        Example usage:

        Budget detail has allocate budget:
            Plan Detail Line | Analytic Account | Fund  | Tags | Allocated | ...
            --------------------------------------------------------------
            1                |               A  | Fund1 | Tag1 |     100.0 | ...
            2                |               A  | Fund2 | Tag2 |     100.0 | ...

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
        dates_to_lookup = set()
        valid_doclines_map = {}

        for docline in doclines:
            analytic_field = docline._budget_analytic_field
            if not docline[analytic_field]:
                continue

            valid_doclines_map[docline.id] = docline

            if docline.date_commit:
                dates_to_lookup.add(docline.date_commit)

        periods_map = self._map_commit_dates_to_periods(dates_to_lookup)
        prec_digits = self.env.user.company_id.currency_id.decimal_places
        for docline_id in valid_doclines_map:
            docline = valid_doclines_map[docline_id]
            name = docline.name
            fund_name = docline.fund_id.name
            tag_name = ", ".join(docline.analytic_tag_ids.mapped("name"))

            period_id = False  # ค่าเริ่มต้น
            if docline.date_commit:
                period_id = periods_map.get(docline.date_commit, False)

            if not period_id:
                error_date_str = (
                    str(docline.date_commit) if docline.date_commit else "missing"
                )
                errors.append(
                    self.env._(
                        "Budget period could not be uniquely determined "
                        "for '%(name)s' on date %(date)s.",
                        name=name,
                        date=error_date_str,
                    )
                )
                continue

            try:
                query_dict = self._get_query_dict(docline)
            except Exception as e:
                errors.append(f"Error querying budget for {name}: {e}")
                continue

            if not any(x["amount_type"] == "10_budget" for x in query_dict):
                errors.append(
                    self.env._(
                        "%(name)s & %(fund_name)s & %(tag_name)s is not allocated "
                        "on budget plan detail",
                        name=name,
                        fund_name=fund_name,
                        tag_name=tag_name or "False",
                    )
                )
                continue

            total_spend = sum(
                x["amount"]
                for x in query_dict
                if isinstance(x.get("amount"), float)
                and x.get("budget_period_id") == period_id
            )

            # Check that amount after commit is more than 0.0
            if float_compare(total_spend, 0.0, precision_digits=prec_digits) == -1:
                errors.append(
                    self.env._(
                        "%(name)s & %(fund_name)s & %(tag_name)s spend amount "
                        "over budget plan detail limit {:,.2f}",
                        name=name,
                        fund_name=fund_name,
                        tag_name=tag_name or "False",
                    ).format(total_spend)
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
        compute="_compute_plan_detail_all",
    )
    analytic_tag_all = fields.Many2many(
        comodel_name="account.analytic.tag",
        compute="_compute_plan_detail_all",
    )

    def _get_dimension_fields(self):
        return [x for x in self._fields if x.startswith("x_dimension_")]

    @api.depends(
        lambda self: (self._budget_analytic_field,)
        if self._budget_analytic_field
        else ()
    )
    def _compute_plan_detail_all(self):
        for rec in self:
            if not rec[rec._budget_analytic_field]:
                rec.fund_all = False
                rec.analytic_tag_all = False
                continue
            analytics = rec._convert_analytics(rec[rec._budget_analytic_field])
            line_details = analytics.plan_line_detail_ids
            fund_all = line_details.mapped("fund_id")
            rec.fund_all = fund_all
            rec.analytic_tag_all = line_details.mapped("analytic_tag_ids")
            # Default if lenght is 1
            if len(fund_all) == 1:
                rec.fund_id = fund_all.id
            if rec.fund_id and rec.fund_id not in fund_all:
                rec.fund_id = False


class BudgetDoclineMixin(models.AbstractModel):
    _inherit = "budget.docline.mixin"

    def _update_budget_commitment(self, budget_vals, analytic, reverse=False):
        budget_vals = super()._update_budget_commitment(
            budget_vals, analytic, reverse=reverse
        )
        budget_vals["fund_id"] = self.fund_id.id
        budget_vals["fund_group_id"] = self.fund_id.fund_group_id.id
        return budget_vals
