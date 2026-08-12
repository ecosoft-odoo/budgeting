# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models
from odoo.exceptions import UserError


class BudgetPeriod(models.Model):
    _inherit = "budget.period"

    project_id = fields.Many2one(
        comodel_name="project.project",
        copy=False,
        ondelete="restrict",
        help="Project that exclusively uses this Lifetime period.",
    )

    def write(self, vals):
        if {"bm_date_from", "bm_date_to"} & vals.keys() and not self.env.context.get(
            "sync_project_lifetime_dates"
        ):
            project_periods = self.filtered(
                lambda period: period.budget_scope == "lifetime" and period.project_id
            )
            if project_periods:
                raise UserError(
                    self.env._(
                        "Change Project Lifetime dates from the Planned Dates on "
                        "Project %(project)s.",
                        project=project_periods[:1].project_id.display_name,
                    )
                )
        return super().write(vals)
