# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    budget_transfer_source_all_ou = fields.Boolean(
        string="Source Budget Control - All OU",
        help="On budget transfer, the user can select a source budget all budgets.",
    )
    budget_transfer_target_all_ou = fields.Boolean(
        string="Target Budget Control - All OU",
        help="On budget transfer, the user can select a target budget all budgets.",
    )
