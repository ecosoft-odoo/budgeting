# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class ContractBudgetMove(models.Model):
    _name = "contract.budget.move"
    _inherit = ["base.budget.move"]
    _description = "Contract Budget Moves"

    contract_id = fields.Many2one(
        comodel_name="contract.contract",
        related="contract_line_id.contract_id",
        readonly=True,
        store=True,
        index=True,
    )
    contract_line_id = fields.Many2one(
        comodel_name="contract.line",
        readonly=True,
        index=True,
        ondelete="cascade",
        help="Commit budget for this contract_line_id",
    )
    move_id = fields.Many2one(
        comodel_name="account.move",
        related="move_line_id.move_id",
        store=True,
        index=True,
    )
    move_line_id = fields.Many2one(
        comodel_name="account.move.line",
        readonly=True,
        index=True,
        help="Uncommit budget from this move_line_id",
    )

    @api.depends("contract_id")
    def _compute_reference(self):
        for rec in self:
            rec.reference = (
                rec.reference if rec.reference else rec.contract_id.display_name
            )
