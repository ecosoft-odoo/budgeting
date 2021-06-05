# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountAnalyticTag(models.Model):
    _inherit = "account.analytic.tag"

    budget_transfer_constraint = fields.Boolean(
        string="Transfer Constraint",
        related="analytic_dimension_id.budget_transfer_constraint",
        help="This field help constraint transfer with same analytic tag",
    )
    analytic_tag_constraint_ids = fields.Many2many(
        string="Transfer to",
        comodel_name="account.analytic.tag",
        relation="tag_other_rel",
        column1="analytic_tag_id",
        column2="other_analytic_tag_id",
        help="This field help transfer cross over analytic tag",
    )
