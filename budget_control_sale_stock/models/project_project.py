# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError


class ProjectProject(models.Model):
    _inherit = "project.project"

    budget_control_scope = fields.Selection(
        selection=[
            ("fiscal", "Fiscal Period"),
            ("lifetime", "Lifetime"),
        ],
        required=True,
        default="fiscal",
        tracking=True,
        help="Fiscal Period creates a separate Budget Control for each year. "
        "Lifetime uses one total cost budget from the Project start to "
        "end date and does not require year-end carry forward.",
    )
    budget_control_count = fields.Integer(
        compute="_compute_budget_control_count",
    )

    def _ensure_lifetime_budget_period(self, reference_period, fallback_date):
        """Create the private multi-year period used by this Project."""
        self.ensure_one()
        if self.budget_control_scope != "lifetime":
            return reference_period
        if not self.account_id:
            raise UserError(
                self.env._(
                    "Project %(project)s needs an analytic account before its "
                    "lifetime budget can be created.",
                    project=self.display_name,
                )
            )

        analytic = self.account_id
        lifetime_period = analytic.budget_period_id.filtered(
            lambda period: period.budget_scope == "lifetime"
            and period.project_id == self
        )
        if lifetime_period:
            return lifetime_period
        other_lifetime_period = analytic.budget_period_id.filtered(
            lambda period: period.budget_scope == "lifetime"
        )
        if other_lifetime_period:
            raise UserError(
                self.env._(
                    "Analytic %(analytic)s already uses Lifetime Budget Period "
                    "%(period)s outside Project %(project)s.",
                    analytic=analytic.display_name,
                    period=other_lifetime_period.display_name,
                    project=self.display_name,
                )
            )

        date_from = self.date_start or fallback_date
        date_to = self.date or reference_period.bm_date_to
        return analytic._create_lifetime_budget_period(
            {
                "name": self.display_name,
                "bm_date_from": date_from,
                "bm_date_to": date_to,
                "project_id": self.id,
            },
            reference_period=reference_period,
        )

    def _check_lifetime_date_change(self, vals):
        if not {"date_start", "date"} & vals.keys():
            return
        for project in self.filtered(
            lambda rec: rec.budget_control_scope == "lifetime"
        ):
            locked_controls = project.account_id.sudo().budget_control_ids.filtered(
                lambda control: control.active
                and control.state not in ("draft", "cancel")
            )
            if locked_controls:
                raise UserError(
                    self.env._(
                        "Set Project Lifetime Budget Control %(control)s to Draft "
                        "before changing the Project dates.",
                        control=locked_controls[:1].display_name,
                    )
                )

    def _sync_lifetime_budget_period_dates(self):
        for project in self.filtered(
            lambda rec: rec.budget_control_scope == "lifetime"
            and rec.date_start
            and rec.date
        ):
            period = project.account_id.budget_period_id.filtered(
                lambda rec, project=project: rec.budget_scope == "lifetime"
                and rec.project_id == project
            )
            if period and (
                period.bm_date_from != project.date_start
                or period.bm_date_to != project.date
            ):
                period.sudo().with_context(sync_project_lifetime_dates=True).write(
                    {
                        "bm_date_from": project.date_start,
                        "bm_date_to": project.date,
                    }
                )

    def write(self, vals):
        if "budget_control_scope" in vals:
            changed = self.filtered(
                lambda project: project.budget_control_scope
                != vals["budget_control_scope"]
            )
            with_controls = changed.filtered(
                lambda project: project.account_id.budget_control_ids.filtered("active")
            )
            if with_controls:
                raise UserError(
                    self.env._(
                        "Budget Scope cannot be changed after Project %(project)s "
                        "has a Budget Control.",
                        project=with_controls[:1].display_name,
                    )
                )
        self._check_lifetime_date_change(vals)
        res = super().write(vals)
        if {"date_start", "date"} & vals.keys():
            self._sync_lifetime_budget_period_dates()
        return res

    @api.depends(
        "account_id",
        "account_id.budget_control_ids.active",
        "account_id.budget_control_ids.state",
    )
    def _compute_budget_control_count(self):
        accounts = self.account_id
        grouped = self.env["budget.control"]._read_group(
            [
                ("analytic_account_id", "in", accounts.ids),
                ("active", "=", True),
                ("state", "!=", "cancel"),
            ],
            ["analytic_account_id"],
            ["__count"],
        )
        count_by_account = {account.id: count for account, count in grouped}
        for project in self:
            project.budget_control_count = count_by_account.get(
                project.account_id.id, 0
            )

    def action_open_budget_controls(self):
        self.ensure_one()
        return {
            "name": self.env._("Budget Controls"),
            "type": "ir.actions.act_window",
            "res_model": "budget.control",
            "view_mode": "list,form",
            "domain": [
                ("analytic_account_id", "=", self.account_id.id),
                ("active", "=", True),
                ("state", "!=", "cancel"),
            ],
            "context": {"search_default_current_period": False},
        }
