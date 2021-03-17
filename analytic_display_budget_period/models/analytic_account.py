# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    def name_get(self):
        res = []
        for analytic in self:
            name = ("[%(budget_period)s] %(name)s") % {
                "budget_period": analytic.budget_period_id.name,
                "name": analytic.name,
            }
            res.append((analytic.id, name))
        return res
