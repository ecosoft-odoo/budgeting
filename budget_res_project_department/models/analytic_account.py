# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    is_required_department = fields.Boolean(compute="_compute_is_required")
    is_required_project = fields.Boolean(compute="_compute_is_required")
    project_id = fields.Many2one(comodel_name="res.project")

    @api.depends("group_id")
    def _compute_is_required(self):
        department = self.env.ref(
            "budget_res_project_department.analytic_group_department"
        )
        project = self.env.ref("budget_res_project_department.analytic_group_project")
        for rec in self:
            rec.is_required_department = rec.group_id == department
            rec.is_required_project = rec.group_id == project

    @api.model
    def create(self, vals):
        department_id = vals.get("department_id", False)
        project_id = vals.get("project_id", False)
        # Not allow select project and department
        if department_id and project_id:
            raise UserError(_("You can only select one of department or project."))
        if project_id:
            project_obj = self.env["res.project"].browse(project_id)
            if project_obj.state != "confirm":
                raise UserError(_("Project is not in Confirmed state."))
        return super().create(vals)

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            # If not group analytic, not allow select project and department too.
            if rec.project_id and rec.department_id:
                raise UserError(_("You can only select one of department or project."))
            if rec.project_id and rec.project_id.state != "confirm":
                raise UserError(_("Project is not in Confirmed state."))
        return res

    def _find_next_analytic(self, next_date_range):
        """Find next analytic from project or department"""
        next_analytic = super()._find_next_analytic(next_date_range)
        if not next_analytic:
            dimension_analytic = self.project_id or self.department_id
            next_analytic = dimension_analytic.analytic_account_ids.filtered(
                lambda l: l.bm_date_from == next_date_range
            )
        return next_analytic
