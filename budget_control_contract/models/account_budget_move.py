# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountBudgetMove(models.Model):
    _inherit = "account.budget.move"

    @api.depends("move_id")
    def _compute_source_document(self):
        res = super()._compute_source_document()
        for rec in self.filtered("move_line_id.contract_line_id.contract_id"):
            rec.source_document = (
                rec.source_document
                or rec.move_line_id.contract_line_id.contract_id.name
            )
        return res