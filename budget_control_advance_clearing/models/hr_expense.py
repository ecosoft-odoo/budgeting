# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HRExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    advance_budget_move_ids = fields.One2many(
        comodel_name="advance.budget.move",
        inverse_name="sheet_id",
    )

    @api.constrains("advance_sheet_id", "expense_line_ids")
    def _check_analtyic_advance(self):
        """ To clear advance, analytic must equal to the clear advance's """
        clear_advances = self.filtered("advance_sheet_id")
        for sheet in clear_advances:
            advance = sheet.advance_sheet_id
            adv_analytic = advance.expense_line_ids.mapped(
                "analytic_account_id"
            )
            if (
                sheet.expense_line_ids.mapped("analytic_account_id")
                != adv_analytic
            ):
                raise UserError(
                    _(
                        "All selected analytic must equal to its clearing advance: %s"
                    )
                    % adv_analytic.display_name
                )

    def write(self, vals):
        """ Clearing for its Advance """
        res = super().write(vals)
        if vals.get("state") in ("approve", "cancel"):
            clearings = self.filtered("advance_sheet_id")
            clearings.mapped("expense_line_ids").uncommit_advance_budget()
        return res


class HRExpense(models.Model):
    _inherit = "hr.expense"

    advance_budget_move_ids = fields.One2many(
        comodel_name="advance.budget.move",
        inverse_name="expense_id",
    )

    def _get_account_move_by_sheet(self):
        # When advance create move, do set not_affect_budget = True
        move_grouped_by_sheet = super()._get_account_move_by_sheet()
        for sheet in self.mapped("sheet_id").filtered("advance"):
            move_grouped_by_sheet[sheet.id].not_affect_budget = True
        return move_grouped_by_sheet

    def recompute_budget_move(self):
        # Expenses
        expenses = self.filtered(lambda l: not l.advance)
        super(HRExpense, expenses).recompute_budget_move()
        # Advances
        advances = self.filtered(lambda l: l.advance).with_context(
            alt_budget_move_model="advance.budget.move",
            alt_budget_move_field="advance_budget_move_ids",
        )
        super(HRExpense, advances).recompute_budget_move()

    def commit_budget(self, reverse=False, **kwargs):
        if self.advance:
            self = self.with_context(
                alt_budget_move_model="advance.budget.move",
                alt_budget_move_field="advance_budget_move_ids",
            )
        return super().commit_budget(reverse=reverse, **kwargs)

    def uncommit_advance_budget(self):
        """For clearing in valid state, do uncommit for related Advance."""
        for clearing in self.filtered("can_commit"):
            cl_state = clearing.sheet_id.state
            if cl_state in ("approve", "done"):
                # !!! There is no direct reference between advance and c    learing !!!
                # for advance in clearing.advance_line_ids:
                # There is only 1 line of advance, but we want write this same as others
                for (
                    advance
                ) in clearing.sheet_id.advance_sheet_id.expense_line_ids:
                    advance.commit_budget(
                        reverse=True, clearing_id=clearing.id
                    )
            else:
                # Cancel or draft, not commitment line
                self.env["advance.budget.move"].search(
                    [("clearing_id", "=", clearing.id)]
                ).unlink()
