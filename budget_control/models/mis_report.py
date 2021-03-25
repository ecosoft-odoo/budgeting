# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class MisReport(models.Model):
    _inherit = "mis.report"

    def get_kpis(self, company):
        """ By default the kpis is by account_id """
        self.ensure_one()
        kpis = self.get_kpis_by_account_id(company)
        return kpis
