# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountAccount(models.Model):
    _inherit = "account.account"

    budget_bypass = fields.Boolean(
        string="Bypass Budget Control",
        help="When enabled, transactions using this account will skip budget "
        "control checks even if the analytic account is budget-controlled.",
    )
