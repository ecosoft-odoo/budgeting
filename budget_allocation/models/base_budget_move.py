# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.exceptions import UserError


class BaseBudgetMove(models.AbstractModel):
    _inherit = "base.budget.move"

    def _get_domain_budget_move(self, analytic_account_id):
        return [("analytic_account_id", "=", analytic_account_id.id)]

    def _get_budget_allocation_lines(self, analytic_account_id, period_id):
        return analytic_account_id.allocation_line_ids.filtered(
            lambda l: l.analytic_account_id == analytic_account_id
            and l.budget_period_id == period_id
        )

    def _get_fields_read_group(self):
        return ["analytic_account_id", "debit"]

    def _get_groupby_read_group(self):
        return ["analytic_account_id"]

    def _get_ba_line_group(self, budget_allocation_lines, obj_group):
        return budget_allocation_lines

    def _get_move_commit(self, obj, obj_group):
        return obj

    @api.model
    def check_budget_constraint(self, docline):
        """
        Based in input budget_moves, i.e., account_move_line
        1. Get analytic account from commitment
        2. Find budget allocation line with same analytic account
        3. Find all budget move from analytic account
        4. Group by budget move
        5. Check amount commitment and budget allocation amount

        Note: This is a base functional, you can used function by automation action
        or manual call function.
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
        BudgetControl = self.env["budget.control"]
        BudgetPeriod = self.env["budget.period"]
        date_commit = docline.mapped(docline._budget_date_commit_fields[0])
        doc = docline[docline._doc_rel]
        period_id = BudgetPeriod._get_eligible_budget_period(
            date=date_commit[0]
        )
        fields_readgroup = self._get_fields_read_group()
        groupby_readgroup = self._get_groupby_read_group()
        analytic_account = self.mapped("analytic_account_id")
        document = docline._doc_rel
        # check budget move name for filter
        if doc._name == "purchase.order":
            document = "purchase_id"
        elif doc._name == "purchase.request":
            document = "purchase_request_id"
        for aa in analytic_account:
            domain_readgroup = [
                ("analytic_account_id", "=", aa.id),
                (document, "=", doc.id),
            ]
            # Find allocation line group by
            budget_allocation_lines = self._get_budget_allocation_lines(
                aa, period_id
            )
            # get all budget move with analytic
            domain_budget_move = self._get_domain_budget_move(aa)
            budget_moves = BudgetControl.get_move_commit(domain_budget_move)
            for obj in budget_moves:
                if obj._name != self._name:
                    continue
                obj_groups = obj.read_group(
                    domain=domain_readgroup,
                    fields=fields_readgroup,
                    groupby=groupby_readgroup,
                    lazy=False,
                )
                # check line amount can not commit over budget allocation
                for obj_group in obj_groups:
                    ba_line_group = self._get_ba_line_group(
                        budget_allocation_lines, obj_group
                    )
                    # Spend budget is not allocated
                    if not ba_line_group:
                        raise UserError(
                            _(
                                "Can not spend amount because budget is not "
                                "allocated on budget allocation"
                            )
                        )
                    ba_amount = sum(ba_line_group.mapped("released_amount"))
                    # Group by analytic in move commit must less than or
                    # equal budget allocation amount.
                    if obj_group["debit"] > ba_amount:
                        raise UserError(
                            _(
                                "{} spend amount over budget allocation "
                                "limit {:,.2f}".format(
                                    aa.display_name,
                                    (obj_group["debit"] - ba_amount),
                                )
                            )
                        )
                    move_commit = self._get_move_commit(obj, obj_group)
                    amount_commit = sum(move_commit.mapped("debit"))
                    # Total spend move commit with the same group analytic account
                    # must less than or equal budget allocation amount.
                    if amount_commit > ba_amount:
                        raise UserError(
                            _(
                                "{} spend total amount over "
                                "budget allocation limit {:,.2f}".format(
                                    aa.display_name,
                                    (amount_commit - ba_amount),
                                )
                            )
                        )
