# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import models


class ResProject(models.Model):
    _inherit = "res.project"

    def _prepare_analytic_dict_vals(
        self,
        group_id,
        date_from,
        date_to,
        auto_adjust_date_commit,
        period=False,
    ):
        self.ensure_one()
        return {
            "name": self.name,
            "code": self.code,
            "project_id": self.id,  # Project
            "group_id": group_id and group_id.id or False,
            "budget_period_id": period and period.id,
            "bm_date_from": date_from,
            "bm_date_to": date_to,
            "auto_adjust_date_commit": auto_adjust_date_commit,
        }
