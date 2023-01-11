# Copyright 2021 Ecosoft (<http://ecosoft.co.th>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetTransfer(models.Model):
    _inherit = ["budget.transfer", "base.substate.mixin"]
    _name = "budget.transfer"
    _state_field = "state"
