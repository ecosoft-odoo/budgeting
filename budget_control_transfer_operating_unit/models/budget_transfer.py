# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from odoo import fields, models


class BudgetTransfer(models.Model):
    _inherit = "budget.transfer"

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        string="Operating Unit",
        default=lambda self: (
            self.env["res.users"].operating_unit_default_get(self.env.uid)
        ),
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
