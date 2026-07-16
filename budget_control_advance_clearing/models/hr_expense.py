# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


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
        # The batch helper preserves date_commit per expense line.  A mapped
        # list cannot represent different dates in one context and is not a
        # valid value for fields.Date.to_date().
        advance_date_commit = self.env.context.get("force_date_commit", False)

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

    def _get_sorted_clearings(self):
        """Keep the allocation order used by the former per-line implementation."""
        clearing_approved = self.filtered("date_commit")
        clearing_not_approved = self - clearing_approved
        return (
            clearing_approved.sorted(key=lambda clearing: clearing.date_commit)
            + clearing_not_approved
        )

    def _get_clearing_advance_data(self, clearing, cache, remaining):
        """Cache invariant advance data and validate the analytic distribution."""
        advance_sheet = clearing.sheet_id.advance_sheet_id
        if advance_sheet.id not in cache:
            advance_lines = advance_sheet.expense_line_ids
            advances = advance_lines.filtered("amount_commit")
            analytic_ids = set()
            for advance in advance_lines:
                analytic_ids.update(advance.fwd_analytic_distribution or {})
                analytic_ids.update(advance.analytic_distribution or {})
            cache[advance_sheet.id] = (advances, analytic_ids)
            for advance in advances:
                for analytic_id, amount in (advance.amount_commit or {}).items():
                    remaining[(advance.id, analytic_id)] = amount

        advances, advance_analytic_ids = cache[advance_sheet.id]
        if any(
            analytic_id not in advance_analytic_ids
            for analytic_id in clearing.analytic_distribution
        ):
            raise UserError(
                self.env._(
                    "Analytic distribution mismatch. "
                    "Please align with the original advance."
                )
            )
        return advances

    def _prepare_advance_for_batch(self, advance, prepared_advances):
        if advance.id not in prepared_advances:
            batch_advance = advance.with_context(
                alt_budget_move_model="advance.budget.move",
                alt_budget_move_field="advance_budget_move_ids",
            )
            batch_advance.prepare_commit()
            can_create = batch_advance.can_commit and (
                self.env.context.get("force_commit")
                or batch_advance._valid_commit_state()
            )
            prepared_advances[advance.id] = batch_advance if can_create else False
        return prepared_advances[advance.id]

    def _prepare_advance_uncommit_entries(self):
        AnalyticAccount = self.env["account.analytic.account"]
        config_budget_include_tax = self.env.company.budget_include_tax
        force_commit = self.env.context.get("force_commit")
        advance_cache = {}
        remaining = {}
        prepared_advances = {}
        entries = []
        draft_clearing_ids = []

        for clearing in self._get_sorted_clearings():
            if not force_commit and clearing.sheet_id.state not in (
                "approve",
                "post",
                "done",
            ):
                draft_clearing_ids.append(clearing.id)
                continue

            advances = self._get_clearing_advance_data(
                clearing, advance_cache, remaining
            )
            if not advances:
                continue
            origin_amount = (
                clearing.total_amount_currency
                if config_budget_include_tax
                else clearing.untaxed_amount_currency
            )
            for analytic_id, percent in clearing.analytic_distribution.items():
                clearing_amount = origin_amount * (percent / 100)
                analytic = AnalyticAccount.browse(int(analytic_id))
                for advance in advances:
                    remaining_key = (advance.id, str(analytic_id))
                    available = remaining.get(remaining_key, 0.0)
                    if not available:
                        continue
                    amount = min(available, clearing_amount)
                    remaining[remaining_key] -= amount
                    clearing_amount -= amount
                    batch_advance = self._prepare_advance_for_batch(
                        advance, prepared_advances
                    )
                    if not batch_advance:
                        return False, draft_clearing_ids
                    commit_kwargs = {
                        "clearing_id": clearing.id,
                        "amount_currency": amount,
                        "analytic_account_id": analytic,
                        "date": clearing.date_commit,
                    }
                    entries.append(
                        (
                            batch_advance,
                            commit_kwargs,
                            batch_advance._prepare_commit_vals(
                                reverse=True, **commit_kwargs
                            ),
                        )
                    )
                    if clearing_amount <= 0:
                        break
        return entries, draft_clearing_ids

    def _entries_can_create_in_batch(self, entries):
        entries_by_sheet = {}
        for entry in entries:
            entries_by_sheet.setdefault(entry[0].sheet_id.id, []).append(entry)
        for sheet_entries in entries_by_sheet.values():
            existing_moves = sheet_entries[0][0].sheet_id.advance_budget_move_ids
            projected_debit = sum(existing_moves.mapped("debit"))
            projected_credit = sum(existing_moves.mapped("credit"))
            for _advance, _commit_kwargs, vals_list in sheet_entries:
                projected_debit += sum(vals["debit"] for vals in vals_list)
                projected_credit += sum(vals["credit"] for vals in vals_list)
                if float_compare(projected_credit, projected_debit, 2) == 1:
                    return False
        return True

    def _create_advance_uncommit_entries(self, entries):
        budget_moves = self.env["advance.budget.move"]
        if not entries:
            return budget_moves
        if not self._entries_can_create_in_batch(entries):
            for advance, commit_kwargs, _vals in entries:
                budget_moves |= advance.commit_budget(reverse=True, **commit_kwargs)
            return budget_moves

        budget_vals = []
        move_period_dates = []
        for advance, _commit_kwargs, vals_list in entries:
            budget_vals.extend(vals_list)
            move_period_dates.extend([advance.date_commit] * len(vals_list))
        budget_moves = budget_moves.create(budget_vals)
        period_dates = dict(zip(budget_moves.ids, move_period_dates, strict=False))
        self._update_template_line_batch(budget_moves, period_dates=period_dates)
        return budget_moves

    def uncommit_advance_budget(self):
        """Return clearing amounts in legacy order, then create moves in bulk."""
        entries, draft_clearing_ids = self._prepare_advance_uncommit_entries()
        if entries is False:
            # This can only happen for an invalid advance state.  Preserve the
            # old behavior by letting commit_budget() handle the entries one by one.
            return self._uncommit_advance_budget_sequential()
        budget_moves = self._create_advance_uncommit_entries(entries)
        if draft_clearing_ids:
            self.env["advance.budget.move"].search(
                [("clearing_id", "in", draft_clearing_ids)]
            ).unlink()
        return budget_moves

    def _uncommit_advance_budget_sequential(self):
        """Compatibility path for an unexpected invalid advance state."""
        budget_moves = self.env["advance.budget.move"]
        AnalyticAccount = self.env["account.analytic.account"]
        config_budget_include_tax = self.env.company.budget_include_tax
        for clearing in self._get_sorted_clearings():
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
                self.env["advance.budget.move"].search(
                    [("clearing_id", "=", clearing.id)]
                ).unlink()
        return budget_moves

    def _get_move_line_dst(
        self,
        move_line_name,
        partner_id,
        total_amount,
        total_amount_currency,
        account_advance,
    ):
        ml_dst_dict = super()._get_move_line_dst(
            move_line_name,
            partner_id,
            total_amount,
            total_amount_currency,
            account_advance,
        )
        ml_dst_dict["not_affect_budget"] = True
        return ml_dst_dict
