# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from psycopg2 import sql

from odoo import _, api, models
from odoo.tools import float_compare


class BaseBudgetMove(models.AbstractModel):
    _inherit = "base.budget.move"

    def _get_where_commitment(self, docline):
        return "analytic_account_id = {} and active = True".format(
            docline[docline._budget_analytic_field].id
        )

    def _get_table_query(self):
        """
        Query from budget monitoring,
        if not install budget_source_fund module
        """
        model = "source.fund.monitor.report"
        if self.env.get(model, "/") == "/":
            model = "budget.monitor.report"
        return self.env[model].with_context(force_all_ou=1)._table_query

    def _get_query_dict(self, docline):
        self._cr.execute(
            sql.SQL(
                """
            SELECT * FROM ({monitoring}) report
            WHERE {where_query_commitment}""".format(
                    monitoring=self._get_table_query(),
                    where_query_commitment=self._get_where_commitment(docline),
                )
            )
        )
        return self.env.cr.dictfetchall()

    @api.model
    def check_budget_allocation_limit(self, doclines):
        """
        Check amount with budget allocation,
        Based on source fund monitoring.
        1. Check analytic account from commitment
        2. Find budget allocation line from condition with monitoring
        3. Calculated Released amount on budget allocation (2) - commitment
            is not negative (1)

        Note: This is a base functional, you can used it by server action or install
        module budget_constraint.
        ==============================================================
        Condition constraint (Ex. Invoice Lines)
            - Budget Allocation has allocation analytic A = 100.0
            - User can used
        --------------------------------------------------------------
        Document | Line | Analytic Account |  Amount |
        --------------------------------------------------------------
        INV001   |    1 |             A    |   130.0 | >>>>> Over Limit
        ----------------------------Confirm----------------------------
        INV002   |    1 |             A    |    10.0 |
        INV002   |    2 |             A    |    60.0 | >>>>> Pass, balance 30
        ----------------------------Confirm----------------------------
        INV003   |    1 |             A    |    10.0 |
        INV003   |    2 |             A    |    60.0 | >>>>> Over Limit
        """
        # Base on source fund monitoring
        message_error = []
        for docline in doclines:
            if not docline[docline._budget_analytic_field]:
                continue
            query_dict = self._get_query_dict(docline)
            if not any(x["amount_type"] == "1_budget" for x in query_dict):
                message_error.append(
                    _("{} is not allocated on budget allocation".format(docline.name))
                )
                continue
            total_spend = sum(
                [x["amount"] for x in query_dict if isinstance(x["amount"], float)]
            )
            # check amount after commit must have more than 0.0
            prec_digits = self.env.user.company_id.currency_id.decimal_places
            if float_compare(total_spend, 0.0, precision_digits=prec_digits) == -1:
                message_error.append(
                    _(
                        "{} spend amount over budget allocation "
                        "limit {:,.2f}".format(docline.name, total_spend)
                    )
                )
        return message_error
