# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, models


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

    @api.model
    def name_search(self, name, args=None, operator="ilike", limit=100):
        args = args or []
        domain = []
        if name:
            domain = [
                "|",
                "|",
                ("code", operator, name),
                ("budget_period_id", operator, name),
                ("name", operator, name),
            ]
        invoices = self.search(domain + args, limit=limit)
        return invoices.name_get()
