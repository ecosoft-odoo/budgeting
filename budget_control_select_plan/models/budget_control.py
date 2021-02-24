# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, models


class BudgetControl(models.Model):
    _inherit = "budget.control"

    def action_select_plan(self):
        return {
            "name": _("Generate Budget Control Sheet"),
            "res_model": "generate.kpi",
            "view_mode": "form",
            "context": {
                "active_model": "budget.plan",
                "active_ids": self.ids,
            },
            "target": "new",
            "type": "ir.actions.act_window",
        }

    def _domain_kpi_expression(self):
        domain_kpi = super()._domain_kpi_expression()
        kpi_ids = self._context.get("kpi_ids", False)
        kpi_id = False
        create_revision = self._context.get("create_revision", False)
        if kpi_ids and create_revision:
            analytic_id = self.analytic_account_id.id
            kpi = list(
                filter(
                    lambda kpi: kpi.get(analytic_id, False),
                    kpi_ids,
                )
            )
            if kpi:
                kpi_id = kpi[0].get(analytic_id)
            domain_kpi.append(("kpi_id.id", "in", kpi_id))
        return domain_kpi
