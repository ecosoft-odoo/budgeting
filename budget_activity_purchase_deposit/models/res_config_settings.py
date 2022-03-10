# Copyright 2020 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    default_purchase_deposit_activity_id = fields.Many2one(
        comodel_name="budget.activity",
        string="Purchase Deposit Activity",
        default_model="purchase.advance.payment.inv",
        help="Default activity used for payment advances.",
    )
