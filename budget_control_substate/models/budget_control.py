# Copyright 2021 Ecosoft (<http://ecosoft.co.th>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetControl(models.Model):
    _inherit = ["budget.control", "base.substate.mixin"]
    _name = "budget.control"
    _state_field = "state"
