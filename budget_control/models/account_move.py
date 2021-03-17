# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    not_affect_budget = fields.Boolean(
        string="Not Affect Budget",
        readonly=True,
        states={"draft": [("readonly", False)]},
        help="If checked, lines does not create budget move",
    )
    budget_move_ids = fields.One2many(
        comodel_name="account.budget.move",
        inverse_name="move_id",
        string="Account Budget Moves",
    )

    def recompute_budget_move(self):
        self.mapped("invoice_line_ids").recompute_budget_move()

    def _write(self, vals):
        """
        - Commit budget when state changes to actual
        - Cancel/Draft document should delete all budget commitment
        """
        res = super()._write(vals)
        if vals.get("state") in ("posted", "cancel", "draft"):
            for move in self:
                invoice_lines = move.mapped("invoice_line_ids")
                analytics = invoice_lines.mapped("analytic_account_id")
                if not move.not_affect_budget:
                    analytics._check_budget_control_status()
                for line in invoice_lines:
                    line.commit_budget()
        return res

    def _move_type_budget(self):
        """For hooks, default check budget following
        - Vedor Bills
        - Customer Refund
        - Journal Entries
        """
        self.ensure_one()
        return ("in_invoice", "out_refund", "entry")

    def action_post(self):
        res = super().action_post()
        BudgetPeriod = self.env["budget.period"]
        move_check_budget = self.filtered(
            lambda l: l.move_type in self._move_type_budget()
        )
        for doc in move_check_budget:
            BudgetPeriod.check_budget(doc.budget_move_ids)
        return res
