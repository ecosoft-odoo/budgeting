# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountAssetTransferLine(models.TransientModel):
    _name = "account.asset.transfer.line"
    _inherit = [
        "analytic.dimension.line",
        "account.asset.transfer.line",
        "budget.docline.mixin.base",
    ]
    _analytic_tag_field_name = "analytic_tag_ids"
