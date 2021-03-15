# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from odoo import fields, models


class BudgetTransfer(models.Model):
    _inherit = "budget.transfer"

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        default=lambda self: self.env[
            "res.users"
        ].operating_unit_default_get(),
        help="This operating unit will be defaulted in the move lines.",
    )
