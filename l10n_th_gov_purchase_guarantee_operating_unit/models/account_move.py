# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.onchange("guarantee_ids")
    def _onchange_guarantee_ids(self):
        res = super()._onchange_guarantee_ids()
        for rec in self.filtered("guarantee_ids"):
            rec.operating_unit_id = rec.guarantee_ids[0].operating_unit_id.id
        return res

    @api.onchange("return_guarantee_ids")
    def _onchange_return_guarantee_ids(self):
        res = super()._onchange_return_guarantee_ids()
        for rec in self.filtered("return_guarantee_ids"):
            rec.operating_unit_id = rec.return_guarantee_ids[0].operating_unit_id.id
        return res
