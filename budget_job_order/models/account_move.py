# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _prepare_analytic_line(self):
        res = super()._prepare_analytic_line()
        for i, ml in enumerate(self):
            res[i]["job_order_id"] = ml.job_order_id.id
        return res
