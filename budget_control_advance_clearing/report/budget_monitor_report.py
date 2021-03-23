# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BudgetMonitorReport(models.Model):
    _inherit = "budget.monitor.report"

    res_id = fields.Reference(
        selection_add=[("hr.expense", "Expense")],
    )
    amount_type = fields.Selection(
        selection_add=[("4_av_commit", "AV Commit")],
    )

    def _select_av_commit(self):
        return [
            """
            4000000000 + a.id as id,
            'hr.expense,' || a.expense_id as res_id,
            a.analytic_account_id,
            a.analytic_group,
            a.date as date,
            '4_av_commit' as amount_type,
            a.credit-a.debit as amount,
            a.product_id,
            a.account_id,
            b.name as reference
       """
        ]

    def _from_av_commit(self):
        return """
            from advance_budget_move a
            left outer join hr_expense_sheet b on a.sheet_id = b.id
        """

    def _get_sql(self):
        select_av_query = self._select_av_commit()
        select_av = ", ".join(sorted(select_av_query))
        return super()._get_sql() + "union (select {} {})".format(
            select_av,
            self._from_av_commit(),
        )
