# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, models


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    def name_get(self):
        res = []
        for analytic in self:
            name = analytic.name
            if analytic.code:
                name = ("[%(code)s] %(name)s") % {
                    "code": analytic.code,
                    "name": name,
                }
            if analytic.partner_id:
                name = _("%(name)s - %(partner)s") % {
                    "name": name,
                    "partner": analytic.partner_id.commercial_partner_id.name,
                }
            if analytic.budget_period_id:
                name = ("[%(budget_period)s] %(name)s") % {
                    "budget_period": analytic.budget_period_id.name,
                    "name": name,
                }
            res.append((analytic.id, name))
        return res
