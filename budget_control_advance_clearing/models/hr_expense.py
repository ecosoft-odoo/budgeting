# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError


class HRExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    advance_budget_move_ids = fields.One2many(
        comodel_name="advance.budget.move",
        inverse_name="sheet_id",
    )

    def write(self, vals):
        """Clearing for its Advance and Cancel payment expense"""
        res = super().write(vals)
        if vals.get("approval_state") in ("approve", "cancel", False):
            # If this is a clearing, return commit to the advance
            advances = self.mapped("advance_sheet_id.expense_line_ids")
            if advances:
                advances.recompute_budget_move()
        return res

    def _prepare_clear_advance(self, line):
        """Cleaing after carry forward Advance"""
        clearing_dict = super()._prepare_clear_advance(line)
        if clearing_dict.get("analytic_account_id") and clearing_dict.get(
            "fwd_analytic_account_id"
        ):
            clearing_dict["analytic_account_id"] = clearing_dict[
                "fwd_analytic_account_id"
            ]
            clearing_dict["date_commit"] = False
        return clearing_dict

    def _prepare_bills_vals(self):
        """Not affect budget for advance"""
        self.ensure_one()
        res = super()._prepare_bills_vals()
        if self.advance:
            res["not_affect_budget"] = True
        return res

    def unlink(self):
        # Recompute budget advance after unlink
        advance = self.advance_sheet_id
        res = super().unlink()
        advance.recompute_budget_move()
        return res


class HRExpense(models.Model):
    _inherit = "hr.expense"

    advance_budget_move_ids = fields.One2many(
        comodel_name="advance.budget.move",
        inverse_name="expense_id",
    )

    def _filter_current_move(self, analytic):
        self.ensure_one()
        if self._context.get("advance", False):
            return self.advance_budget_move_ids.filtered(
                lambda advance_move, analytic=analytic: advance_move.analytic_account_id
                == analytic
            )
        return super()._filter_current_move(analytic)

    @api.depends("advance_budget_move_ids", "budget_move_ids", "budget_move_ids.date")
    def _compute_commit(self):
        advances = self.filtered("advance")
        expenses = self - advances
        # Advances
        for rec in advances:
            analytic_distribution = rec[self._budget_analytic_field]
            # Add analytic_distribution from forward_commit
            if rec.fwd_analytic_distribution:
                for analytic_id, aa_percent in rec.fwd_analytic_distribution.items():
                    analytic_distribution[analytic_id] = aa_percent

            if not analytic_distribution:
                continue

            # Compute amount commit each analytic
            amount_commit_json = {}
            for analytic_id in analytic_distribution:  # Get id only
                budget_move = rec.advance_budget_move_ids.filtered(
                    lambda move, analytic_id=analytic_id: move.analytic_account_id.id
                    == int(analytic_id)
                )
                debit = sum(budget_move.mapped("debit"))
                credit = sum(budget_move.mapped("credit"))
                amount_commit_json[analytic_id] = debit - credit
            rec.amount_commit = amount_commit_json

            if rec.advance_budget_move_ids:
                rec.date_commit = min(rec.advance_budget_move_ids.mapped("date"))
            else:
                rec.date_commit = False
        # Expenses
        return super(HRExpense, expenses)._compute_commit()

    def _get_recompute_advances(self):
        AnalyticAccount = self.env["account.analytic.account"]
        # date_commit return list, so we check in list again
        advance_date_commit = (
            self.env.context.get("force_date_commit", False)
            or self.mapped("date_commit")[:-1]
            or False
        )

        # Commit Advance
        res = super(
            HRExpense,
            self.with_context(
                alt_budget_move_model="advance.budget.move",
                alt_budget_move_field="advance_budget_move_ids",
                force_date_commit=advance_date_commit,
            ),
        ).recompute_budget_move()

        advance_sheet = self.mapped("sheet_id")
        advance_sheet.ensure_one()

        # For case return advance
        for payment in advance_sheet.payment_return_ids:
            ml_credit = payment.move_id.line_ids.filtered("credit").filtered(
                "reconciled"
            )
            advance = ml_credit.expense_id

            if not advance:
                continue

            analytic_distribution = advance[self._budget_analytic_field]
            # Check return advance after carry forword
            if advance.fwd_analytic_distribution:
                analytic_accounts = {
                    int(aid): AnalyticAccount.browse(int(aid))
                    for aid in advance.fwd_analytic_distribution
                }
                payment_after_carry = False
                for (
                    analytic_id,
                    aa_percent,
                ) in advance.fwd_analytic_distribution.items():
                    analytic = analytic_accounts[int(analytic_id)]
                    # Check if payment falls within the analytic account's
                    # budget date range
                    if analytic.bm_date_to >= payment.date >= analytic.bm_date_from:
                        advance.commit_budget(
                            amount_currency=ml_credit.amount_currency
                            * (aa_percent / 100),
                            move_line_id=ml_credit.id,
                            analytic_account_id=analytic,
                            date=payment.date,
                        )
                        payment_after_carry = True

                if payment_after_carry:
                    continue
            # Return advance with normal case
            analytic_accounts = {
                int(aid): AnalyticAccount.browse(int(aid))
                for aid in analytic_distribution
            }
            for analytic_id, aa_percent in analytic_distribution.items():
                analytic = analytic_accounts[int(analytic_id)]
                advance.commit_budget(
                    amount_currency=ml_credit.amount_currency * (aa_percent / 100),
                    move_line_id=ml_credit.id,
                    analytic_account_id=analytic,
                    date=payment.date,
                )

        # For case clearing, uncommit them from advance
        clearings = self.search(
            [("sheet_id.advance_sheet_id", "=", advance_sheet.id)], order="id"
        )
        clearings.uncommit_advance_budget()
        return res

    # def _close_budget_sheets_with_adj_commit(self):
    #     advance_budget_moves = self.filtered("advance_budget_move_ids.adj_commit")
    #     for sheet in advance_budget_moves.mapped("sheet_id"):
    #         # And only if some adjustment has occured
    #         adj_moves = sheet.advance_budget_move_ids.filtered("adj_commit")
    #         moves = sheet.advance_budget_move_ids - adj_moves
    #         # If adjust > over returned
    #         adjusted = sum(adj_moves.mapped("debit"))
    #         over_returned = sum(moves.mapped(lambda l: l.credit - l.debit))
    #         if adjusted > over_returned:
    #             sheet.close_budget_move()

    def recompute_budget_move(self):
        if not self:
            return
        # Recompute budget moves for expenses
        expenses = self.filtered(lambda sheet: not sheet.advance)
        res = super(HRExpense, expenses).recompute_budget_move()

        # Recompute budget moves for advances
        advance = self - expenses
        if advance:
            advance._get_recompute_advances()
            # NOTE: Return advance, commit again because
            # it will lose from clearing uncommit
            # Only when advance is over returned, do close_budget_move() to final adjust
            # Note: now, we only found case in Advance / Return / Clearing case
            # NOTE: Test with no do this method.
            # advance._close_budget_sheets_with_adj_commit()
        return res

    def close_budget_move(self):
        # Expenses
        expenses = self.filtered(lambda sheet: not sheet.advance)
        super(HRExpense, expenses).close_budget_move()

        # Advances
        advances = self - expenses
        advances = advances.with_context(
            alt_budget_move_model="advance.budget.move",
            alt_budget_move_field="advance_budget_move_ids",
        )
        return super(HRExpense, advances).close_budget_move()

    def commit_budget(self, reverse=False, **vals):
        if self.advance:
            self = self.with_context(
                alt_budget_move_model="advance.budget.move",
                alt_budget_move_field="advance_budget_move_ids",
            )
        return super().commit_budget(reverse=reverse, **vals)

    def uncommit_advance_budget(self):
        """For clearing in valid state,
        do uncommit for related Advance sorted by date commit."""
        budget_moves = self.env["advance.budget.move"]
        AnalyticAccount = self.env["account.analytic.account"]
        # Sorted clearing by date_commit first. for case clearing > advance
        # it should uncommit clearing that approved first
        clearing_approved = self.filtered("date_commit")
        clearing_not_approved = self - clearing_approved
        clearing_sorted = (
            clearing_approved.sorted(key=lambda clearing: clearing.date_commit)
            + clearing_not_approved
        )
        config_budget_include_tax = self.env.company.budget_include_tax
        for clearing in clearing_sorted:
            cl_state = clearing.sheet_id.state
            if self.env.context.get("force_commit") or cl_state in (
                "approve",
                "post",  # clearing more than advance, it change to state post
                "done",
            ):
                # With possibility to have multiple advance lines,
                # just return amount line by line
                origin_clearing_amount_currency = (
                    clearing.total_amount_currency
                    if config_budget_include_tax
                    else clearing.untaxed_amount_currency
                )
                clearing_analytic = clearing.analytic_distribution
                advance_lines = clearing.sheet_id.advance_sheet_id.expense_line_ids

                advances = advance_lines.filtered("amount_commit")
                if not advances:
                    continue

                # Check analytic distribution match with advance
                advance_analytic = {}
                for av_line in advance_lines:
                    if av_line.fwd_analytic_distribution:
                        advance_analytic.update(av_line.fwd_analytic_distribution)
                    advance_analytic.update(av_line.analytic_distribution)
                clearing_analytic_ids = [x for x in clearing_analytic]
                advance_analytic_ids = [x for x in advance_analytic]

                if any(aa not in advance_analytic_ids for aa in clearing_analytic_ids):
                    raise UserError(
                        self.env._(
                            "Analytic distribution mismatch. "
                            "Please align with the original advance."
                        )
                    )
                # Uncommit budget to advance line by line
                for analyic_id, aa_percent in clearing_analytic.items():
                    clearing_amount = origin_clearing_amount_currency * (
                        aa_percent / 100
                    )
                    analytic = AnalyticAccount.browse(int(analyic_id))
                    for advance in advances:
                        if not advance.amount_commit.get(str(analyic_id)):
                            continue
                        clearing_amount_commit = min(
                            advance.amount_commit[str(analyic_id)], clearing_amount
                        )
                        clearing_amount -= clearing_amount_commit
                        budget_move = advance.commit_budget(
                            reverse=True,
                            clearing_id=clearing.id,
                            amount_currency=clearing_amount_commit,
                            analytic_account_id=analytic,  # specific AA to advance
                            date=clearing.date_commit,
                        )
                        budget_moves |= budget_move
                        if clearing_amount <= 0:
                            break
            else:
                # Cancel or draft, not commitment line
                self.env["advance.budget.move"].search(
                    [("clearing_id", "=", clearing.id)]
                ).unlink()
        return budget_moves
