# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BudgetControl(models.Model):
    _inherit = "budget.control"

    amount_contract = fields.Monetary(
        string="Contract",
        compute="_compute_budget_info",
        help="Sum of contract amount",
    )

    def get_move_commit(self, domain):
        budget_move = super().get_move_commit(domain)
        ContractBudgetMove = self.env["contract.budget.move"]
        contract_move = ContractBudgetMove.search(domain)
        if contract_move:
            budget_move.append(contract_move)
        return budget_move
