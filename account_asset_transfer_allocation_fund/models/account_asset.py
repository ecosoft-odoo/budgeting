# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountAsset(models.Model):
    _inherit = "account.asset"

    fund_id = fields.Many2one(
        comodel_name="budget.source.fund",
        string="Fund",
    )
