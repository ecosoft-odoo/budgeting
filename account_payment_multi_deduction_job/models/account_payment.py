# Copyright 2021 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def _get_update_key_list(self):
        res = super()._get_update_key_list()
        return res + ["job_order_id"]

    def _get_update_key_multi_list(self):
        res = super()._get_update_key_multi_list()
        return res + ["job_order_id"]
