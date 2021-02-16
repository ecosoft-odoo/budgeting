# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class BudgetSourceFundPlan(models.Model):
    _name = "budget.source.fund.plan"
    _inherit = ["budget.source.fund.plan", "base.revision"]

    current_revision_id = fields.Many2one(
        comodel_name="budget.source.fund.plan",
    )
    old_revision_ids = fields.One2many(
        comodel_name="budget.source.fund.plan",
    )
    revision_number = fields.Integer(readonly=True)
