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
        required=True,
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
        required=True,
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

    def _get_domain_source_allocation_line(self):
        res = super()._get_domain_source_allocation_line()
        return res + [("fund_id", "=", self.source_fund_id.id)]

    def _get_domain_target_allocation_line(self):
        res = super()._get_domain_target_allocation_line()
        return res + [("fund_id", "=", self.target_fund_id.id)]

    def _check_constraint_transfer(self):
        super()._check_constraint_transfer()
        source_lines, target_lines = self._get_budget_allocation_line()
        source_line_amount = sum(source_lines.mapped("released_amount"))
        if source_line_amount < self.amount:
            raise UserError(
                _(
                    "{} Fund {} can transfer amount not be exceeded {:,.2f}".format(
                        self.source_budget_control_id.name,
                        self.source_fund_id.name,
                        source_line_amount,
                    )
                )
            )

    def _get_message_source_transfer(self):
        source_transfer = super()._get_message_source_transfer()
        return "<br/>Fund: ".join([source_transfer, self.source_fund_id.name])

    def _get_message_target_transfer(self):
        target_transfer = super()._get_message_target_transfer()
        return "<br/>Fund: ".join([target_transfer, self.target_fund_id.name])
