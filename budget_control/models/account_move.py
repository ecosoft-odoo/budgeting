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

    # def _write(self, vals):  TODO: using _write() seem not ok for test script
    def write(self, vals):
        """
        - Commit budget when state changes to actual
        - Cancel/Draft document should delete all budget commitment
        """
        res = super().write(vals)
        if vals.get("state") in ("posted", "cancel", "draft"):
            for move in self:
                invoice_lines = move.mapped("invoice_line_ids")
                for line in invoice_lines:
                    line.commit_budget()
        return res

    def _filtered_move_check_budget(self):
        """For hooks, default check budget following
        - Vedor Bills
        - Customer Refund
        - Journal Entries
        """
        move_types = ["in_invoice", "out_refund", "entry"]
        return self.filtered_domain([("move_type", "in", move_types)])

    def action_post(self):
        res = super().action_post()
        self.flush()
        BudgetPeriod = self.env["budget.period"]
        for move in self._filtered_move_check_budget():
            BudgetPeriod.check_budget(move.budget_move_ids)
        return res
