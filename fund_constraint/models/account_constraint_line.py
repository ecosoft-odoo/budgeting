# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class AccountConstraintLine(models.Model):
    _name = "account.constraint.line"
    _description = "Account Constraint Line"

    fund_constraint_id = fields.Many2one(
        comodel_name="fund.constraint",
        required=True,
    )
    account_ids = fields.Many2many(
        comodel_name="account.account",
        relation="fund_constraint_account_rel",
        column1="account_id",
        column2="fund_constraint_id",
    )
    allocation_amount = fields.Float()
