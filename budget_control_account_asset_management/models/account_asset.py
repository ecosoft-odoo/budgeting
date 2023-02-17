# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountAsset(models.Model):
    _inherit = "account.asset"

    not_affect_budget = fields.Boolean(default=True)
