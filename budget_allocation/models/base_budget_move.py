# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from psycopg2 import sql

from odoo import _, api, models


class BaseBudgetMove(models.AbstractModel):
    _inherit = "base.budget.move"

    def _where_query_source_fund(self, docline):
        return "analytic_account_id = {}".format(
            docline[docline._budget_analytic_field].id
        )

    def _get_dict_source_fund_value(self, docline):
        self._cr.execute(
            sql.SQL(
                """
            SELECT * FROM ({source_fund_monitoring}) report
            WHERE {where_source_fund}""".format(
                    source_fund_monitoring=self.env[
                        "source.fund.monitor.report"
                    ]
                    .with_context(force_all_ou=1)
                    ._table_query,
                    where_source_fund=self._where_query_source_fund(docline),
                )
            )
        )
        return self.env.cr.dictfetchall()

    @api.model
    def check_budget_allocation_limit(self, doclines):
        """
        Check amount with budget allocation,
        Based on source fund monitoring.
        1. Check analytic account from commitment, if not it not check
        2. Find budget allocation line from condition with monitoring
        3. Check commitment is created on budget allocation, if not it will error
        4. Check amount commitment from monitoring, if negative it will error

        Note: This is a base functional, you can used it by server action or install
        module budget_constraint.
        ==============================================================
        Condition constraint (Ex. Invoice Lines)
            - Allocation Analytic A = 100.0
        --------------------------------------------------------------
        Document | Line | Analytic Account |  Amount |
        --------------------------------------------------------------
        INV001   |    1 |             A    |   130.0 | >>>>> Over Limit
        ----------------------------NEXT----------------------------
        INV002   |    1 |             A    |    10.0 |
        INV002   |    2 |             A    |    60.0 | >>>>> Pass, balance 30
        ----------------------------NEXT----------------------------
        INV003   |    1 |             A    |    10.0 |
        INV003   |    2 |             A    |    60.0 | >>>>> Over Limit
        """
        # Base on source fund monitoring
        message_error = []
        for docline in doclines:
            if not docline[docline._budget_analytic_field]:
                continue
            source_fund_dict = self._get_dict_source_fund_value(docline)
            # check commitment must have allocated on budget allocation
            if not any(
                x["amount_type"] == "1_budget" for x in source_fund_dict
            ):
                message_error.append(
                    _(
                        "{} is not allocated on budget allocation".format(
                            docline.name
                        )
                    )
                )
                continue
            total_spend = sum([x["amount"] for x in source_fund_dict])
            # check amount after commit must have more than 0.0
            if total_spend < 0.0:
                message_error.append(
                    _(
                        "{} spend amount over budget allocation "
                        "limit {:,.2f}".format(docline.name, total_spend)
                    )
                )
        return message_error
