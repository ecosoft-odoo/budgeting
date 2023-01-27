# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class TierDefinition(models.Model):
    _inherit = "tier.definition"

    check_budget = fields.Boolean(help="Check budget with tier validation")
