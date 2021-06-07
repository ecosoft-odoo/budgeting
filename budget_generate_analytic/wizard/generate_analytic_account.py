# Copyright 2021 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import _, api, fields, models
from odoo.exceptions import UserError

ALLOW_MODEL_CREATE = ["hr.department", "res.project"]
MODEL_GROUP = {"res.project": "Project", "hr.department": "Department"}
DICT_FIELD_MODEL = {
    "res.project": "project_id",
    "hr.department": "department_id",
}


class GenerateAnalyticAccount(models.TransientModel):
    _name = "generate.analytic.account"
    _description = "Generate Analytic Account"

    budget_period = fields.Many2many(
        comodel_name="budget.period",
        relation="generate_analytic_period_rel",
        column1="analytic_id",
        column2="budget_period_id",
        string="Budget Period",
    )
    group_id = fields.Many2one(
        comodel_name="account.analytic.group",
    )
    analytic_ids = fields.Many2many(
        comodel_name="account.analytic.account",
        compute="_compute_analytic_already_create",
        relation="analytic_ids_rel",
        column1="analytic_id",
        column2="budget_period_id",
        string="Analytic Account",
    )

    @api.depends("budget_period")
    def _compute_analytic_already_create(self):
        self.ensure_one()
        analytics = self.env["account.analytic.account"]
        model, active_ids = self._check_model_allow()
        objects = self.env[model].browse(active_ids)
        analytic_account_ids = objects.mapped("analytic_account_ids")
        period_ids = self.budget_period._origin
        for period_id in period_ids:
            analytics += analytic_account_ids.filtered(
                lambda l: l.budget_period_id == period_id
            )
        self.analytic_ids = analytics

    def _check_model_allow(self):
        model = self._context.get("active_model", False)
        active_ids = self._context.get("active_ids", False)
        if model not in ALLOW_MODEL_CREATE:
            raise UserError(
                _("Model {} is not allow to create analytic.".format(model))
            )
        return model, active_ids

    @api.model
    def default_get(self, default_fields):
        values = super().default_get(default_fields)
        model, active_ids = self._check_model_allow()
        # Check state confirmed on project
        if model == "res.project":
            projects = self.env[model].browse(active_ids)
            if any(project.state != "confirm" for project in projects):
                raise UserError(_("Project must be state Confirmed."))
        # Default group_id from model
        name_group = MODEL_GROUP.get(model, False)
        analytic_group = self.env["account.analytic.group"].search(
            [("name", "=", name_group)]
        )
        values["group_id"] = analytic_group.id
        return values

    def _prepare_analytic_vals(self, objects):
        self.ensure_one()
        analytic_account_ids = objects.mapped("analytic_account_ids")
        budget_period = self.budget_period
        group_id = self.group_id
        analytic_vals = []
        field_model = DICT_FIELD_MODEL[objects._name]
        for obj in objects:
            if not budget_period:
                existing_analytic = analytic_account_ids.filtered(
                    lambda l: not l.budget_period_id
                    and l[field_model].id == obj.id
                )
                if existing_analytic:
                    continue
                val = obj._prepare_analytic_dict_vals(group_id)
                analytic_vals.append(val)
            for period in budget_period:
                existing_analytic = analytic_account_ids.filtered(
                    lambda l: l.budget_period_id == period
                    and l[field_model].id == obj.id
                )
                if existing_analytic:
                    continue
                val = obj._prepare_analytic_dict_vals(group_id, period=period)
                analytic_vals.append(val)
        return analytic_vals

    def action_create_analytic(self):
        model, active_ids = self._check_model_allow()
        objects = self.env[model].browse(active_ids)
        analytic_vals = self._prepare_analytic_vals(objects)
        analytic = self.env["account.analytic.account"].create(analytic_vals)
        list_view = self.env.ref("budget_control.view_budget_analytic_list").id
        form_view = self.env.ref(
            "budget_control.view_account_analytic_account_form"
        ).id
        return {
            "name": _("Analytic Accounts"),
            "type": "ir.actions.act_window",
            "res_model": "account.analytic.account",
            "views": [[list_view, "list"], [form_view, "form"]],
            "view_mode": "list",
            "domain": [("id", "in", analytic and analytic.ids or [])],
        }
