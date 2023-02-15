# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class PurchaseBudgetMove(models.Model):
    _inherit = "purchase.budget.move"

    is_agreement = fields.Boolean()
