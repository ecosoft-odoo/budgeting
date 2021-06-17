# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import models


class ResProject(models.Model):
    _inherit = "res.project"

    def _prepare_analytic_dict_vals(self, group_id, period=False):
        self.ensure_one()
        return {
            "name": "{}{}".format(
                period and period.name + ": " or "", self.name
            ),
            "code": self.code,
            "project_id": self.id,
            "group_id": group_id and group_id.id or False,
            "budget_period_id": period and period.id,
        }