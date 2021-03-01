# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class BudgetControl(models.Model):
    _inherit = "budget.control"

    def _domain_kpi_expression(self):
        """ Update kpi_ids, case budget plan revision """
        kpi_ids = self._context.get("kpi_ids", False)
        ctx = self._context.copy()
        create_revision = self._context.get("create_revision", False)
        if kpi_ids and create_revision:
            kpi_id = False
            analytic_id = self.analytic_account_id.id
            kpi = list(
                filter(
                    lambda kpi: kpi.get(analytic_id, False),
                    kpi_ids,
                )
            )
            if kpi:
                kpi_id = kpi[0].get(analytic_id)
            ctx["kpi_ids"] = kpi_id
        domain_kpi = super(
            BudgetControl, self.with_context(ctx)
        )._domain_kpi_expression()
        return domain_kpi
