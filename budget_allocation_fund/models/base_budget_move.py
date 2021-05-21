# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BaseBudgetMove(models.AbstractModel):
    _inherit = "base.budget.move"

    fund_id = fields.Many2one(
        comodel_name="budget.source.fund",
        string="Fund",
        index=True,
    )
    fund_group_id = fields.Many2one(
        comodel_name="budget.source.fund.group",
        string="Fund Group",
        index=True,
    )


class BudgetDoclineMixin(models.AbstractModel):
    _inherit = "budget.docline.mixin"

    fund_id = fields.Many2one(
        comodel_name="budget.source.fund",
        index=True,
        ondelete="restrict",
    )
    fund_all = fields.Many2many(
        comodel_name="budget.source.fund",
        compute="_compute_fund_all",
        compute_sudo=True,
    )

    def _compute_fund_all(self):
        for doc in self:
            fund_ids = doc[
                doc._budget_analytic_field
            ].allocation_line_ids.mapped("fund_id")
            doc.fund_all = fund_ids
            if len(fund_ids) > 1 and doc.fund_id and doc.fund_id in fund_ids:
                continue
            doc.fund_id = len(fund_ids) == 1 and fund_ids.id or False
