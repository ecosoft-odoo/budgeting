# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    budget_manual_consumed_plan = fields.Boolean(
        string="Manual date on consumed plan",
        help="If checked, all budget will manual date "
        "for update consumed amount on budget control.",
    )
