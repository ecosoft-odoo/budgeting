# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    is_required_department = fields.Boolean(compute="_compute_is_required")
    is_required_project = fields.Boolean(compute="_compute_is_required")

    @api.depends("group_id")
    def _compute_is_required(self):
        department = self.env.ref(
            "budget_control_department.analytic_department_group"
        )
        project = self.env.ref("res_project_analytic.analytic_project_group")
        for rec in self:
            rec.is_required_department = (
                rec.group_id.id == department.id and True or False
            )
            rec.is_required_project = (
                rec.group_id.id == project.id and True or False
            )

    @api.model
    def create(self, vals):
        not_other = self.is_required_department or self.is_required_project
        department_id = vals.get("department_id", False)
        project_id = vals.get("project_id", False)
        if (
            not_other
            and not (department_id or project_id)
            or (department_id and project_id)
        ):
            raise UserError(_("You must have select Department or Project."))
        if project_id:
            project_obj = self.env["res.project"].browse(project_id)
            if project_obj.state != "confirm":
                raise UserError(_("Project is not state Confirmed."))
        return super().create(vals)

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            not_other = rec.is_required_department or rec.is_required_project
            if not_other and (
                (rec.project_id and rec.department_id)
                or not (rec.project_id or rec.department_id)
            ):
                raise UserError(
                    _("You must have select Department or Project.")
                )
            if rec.project_id and rec.project_id.state != "confirm":
                raise UserError(_("Project is not state Confirmed."))
        return res

    def _find_next_analytic(self, next_date_range):
        """ Find next analytic from department """
        next_analytic = super()._find_next_analytic(next_date_range)
        if not next_analytic:
            dimension_analytic = self.department_id
            next_analytic = dimension_analytic.analytic_account_ids.filtered(
                lambda l: l.bm_date_from == next_date_range
            )
        return next_analytic
