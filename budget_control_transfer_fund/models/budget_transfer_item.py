# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class BudgetTransferItem(models.Model):
    _inherit = "budget.transfer.item"

    source_fund_id = fields.Many2one(
        comodel_name="budget.source.fund",
        string="Source Fund",
        ondelete="restrict",
    )
    source_fund_all = fields.Many2many(
        comodel_name="budget.source.fund",
        compute="_compute_source_fund_all",
        compute_sudo=True,
    )
    target_fund_id = fields.Many2one(
        comodel_name="budget.source.fund",
        string="Target Fund",
        ondelete="restrict",
    )
    target_fund_all = fields.Many2many(
        comodel_name="budget.source.fund",
        compute="_compute_target_fund_all",
        compute_sudo=True,
    )

    @api.depends("source_budget_control_id")
    def _compute_source_fund_all(self):
        for doc in self:
            fund_ids = doc.source_budget_control_id.fund_ids
            doc.source_fund_all = fund_ids
            if (
                len(fund_ids) > 1
                and doc.source_fund_id
                and doc.source_fund_id in fund_ids
            ):
                continue
            doc.source_fund_id = len(fund_ids) == 1 and fund_ids.id or False

    @api.depends("target_budget_control_id")
    def _compute_target_fund_all(self):
        for doc in self:
            fund_ids = doc.target_budget_control_id.fund_ids
            doc.target_fund_all = fund_ids
            if (
                len(fund_ids) > 1
                and doc.target_fund_id
                and doc.target_fund_id in fund_ids
            ):
                continue
            doc.target_fund_id = len(fund_ids) == 1 and fund_ids.id or False

    def transfer(self):
        res = super().transfer()
        for transfer in self:
            source_line = (
                transfer.source_budget_control_id.allocation_line_ids.filtered(
                    lambda l: l.fund_id == transfer.source_fund_id
                )
            )
            target_line = (
                transfer.target_budget_control_id.allocation_line_ids.filtered(
                    lambda l: l.fund_id == transfer.target_fund_id
                )
            )
            if not (source_line and target_line):
                raise UserError(_("Invalid source of fund!"))
            source_line[0].budget_amount -= transfer.amount
            target_line[0].budget_amount += transfer.amount
        return res
