# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from collections import defaultdict

from odoo import fields, models


class MisReport(models.Model):
    _inherit = "mis.report"

    is_activity = fields.Boolean(
        help="if check, Expression will compute Activity instead Account"
    )

    def get_kpis(self, company):
        self.ensure_one()
        if self.is_activity:
            return self.get_kpis_by_activity_id(company)
        return super().get_kpis(company)

    def get_kpis_by_activity_id(self, company):
        """ Return { activity_id: set(kpi) } """
        res = defaultdict(set)
        for kpi in self.kpi_ids:
            for expression in kpi.expression_ids:
                if not expression.name:
                    continue
                activity_ids = kpi.budget_activity_group.activity_ids.ids
                for activity_id in activity_ids:
                    res[activity_id].add(kpi)
        return res
