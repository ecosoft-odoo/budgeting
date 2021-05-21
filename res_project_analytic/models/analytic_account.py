# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    project_id = fields.Many2one(comodel_name="res.project")

    def _find_next_analytic(self, next_date_range):
        """ Find next analytic from project """
        next_analytic = super()._find_next_analytic(next_date_range)
        if not next_analytic:
            dimension_analytic = self.project_id
            next_analytic = dimension_analytic.analytic_account_ids.filtered(
                lambda l: l.bm_date_from == next_date_range
            )
        return next_analytic
