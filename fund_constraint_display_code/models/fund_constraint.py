# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class FundConstraint(models.Model):
    _name = "fund.constraint"
    _inherit = ["fund.constraint", "base.display.name"]
    _description = "Fund Constraint display code"
    _field_display = ["number", "name"]
