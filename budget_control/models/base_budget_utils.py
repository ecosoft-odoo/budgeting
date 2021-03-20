# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import _, models
from odoo.exceptions import UserError


class BaseBudgetUtils(models.AbstractModel):
    _name = "base.budget.utils"
    _description = "Base function budget utilization"

    def get_analytic_doc(self, obj):
        """
        Core odoo purchase used field name account_analytic_id
        BUT other used field name analytic_account_id.
        This function will convert name and return <account.analytic.account>
        """
        return obj.mapped("analytic_account_id")

    def next_year_analytic(self, analytic_id):
        """ Find next analytic from analytic date to + 1"""
        dimension_analytic = (
            analytic_id.department_id or analytic_id.project_id
        )
        next_date_range = (
            analytic_id.budget_period_id.bm_date_to + relativedelta(days=1)
        )
        next_analytic = dimension_analytic.analytic_account_ids.filtered(
            lambda l: l.budget_period_id.bm_date_from == next_date_range
        )
        if len(dimension_analytic) > 1:
            raise UserError(_("Analytic date range overlaps."))
        elif not next_analytic:
            raise UserError(
                _(
                    "{}, No analytic for the next date {}.".format(
                        analytic_id.name, next_date_range
                    )
                )
            )
        return next_analytic

    def get_budget_move_ids(self, doc):
        """
        This function will return budget_move_ids BUT
        If you install module budget_control_advance_clearing,
        it will return advance_budget_move_ids
        """
        return doc.mapped("budget_move_ids")

    def _get_budget_move_commit(self, domain):
        return {}

    def get_budget_move(self, doc_type="all", domain=None):
        """
        This function will return value dictionary following your installed module
        - budget_control (account_budget_move)
        - budget_control_expense (expense_budget_move)
        - budget_control_advance_clearing (advance_budget_move)
        - budget_control_purchase (purchase_budget_move)
        - budget_control_purchase_request (purchase_request_budget_move)
        i.e. return {
                'account_budget_move': <object>,
                'expense_budget_move': <object>,
                'advance_budget_move': <object>,
                'purchase_budget_move': <object>,
                'purchase_request_budget_move': <object>,
            }
        """
        budget_move = {}
        if domain is None:
            domain = []
        budget_move_commit = self._get_budget_move_commit(domain)
        if doc_type == "commit":
            return budget_move_commit
        if doc_type == "all":
            budget_move = budget_move_commit
        AccountBudgetMove = self.env["account.budget.move"]
        account_move = AccountBudgetMove.search(domain)
        budget_move["account_budget_move"] = account_move
        return budget_move
