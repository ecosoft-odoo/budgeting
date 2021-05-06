# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BaseBudgetMove(models.AbstractModel):
    _name = "base.budget.move"
    _inherit = ["analytic.dimension.line", "base.budget.move"]
    _analytic_tag_field_name = "analytic_tag_ids"
