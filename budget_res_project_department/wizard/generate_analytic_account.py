# Copyright 2021 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import _, api, fields, models
from odoo.exceptions import UserError

DICT_FIELD_MODEL = {
    "res.project": "project_id",
    "hr.department": "department_id",
}


class GenerateAnalyticAccount(models.TransientModel):
    _name = "generate.analytic.account"
    _description = "Generate Analytic Account"

    budget_period_id = fields.Many2one(comodel_name="budget.period")
    bm_date_from = fields.Date(
        string="Date From",
        compute="_compute_bm_date",
        store=True,
        readonly=False,
        required=True,
        help="Budget commit date must conform with this date",
    )
    bm_date_to = fields.Date(
        string="Date To",
        compute="_compute_bm_date",
        store=True,
        readonly=False,
        required=True,
        help="Budget commit date must conform with this date",
    )
    auto_adjust_date_commit = fields.Boolean(
        string="Auto Adjust Commit Date",
        default=True,
        help="Date From and Date To is used to determine valid date range of "
        "this analytic account when using with budgeting system. If this data range "
        "is setup, but the budget system set date_commit out of this date range "
        "it it can be adjusted automatically.",
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

    @api.depends("budget_period_id")
    def _compute_bm_date(self):
        """Default effective date, but changable"""
        for rec in self:
            rec.bm_date_from = rec.budget_period_id.bm_date_from
            rec.bm_date_to = rec.budget_period_id.bm_date_to

    @api.depends("bm_date_from", "bm_date_to")
    def _compute_analytic_already_create(self):
        self.ensure_one()
        analytics = self.env["account.analytic.account"]
        model = self._context.get("active_model", False)
        active_ids = self._context.get("active_ids", False)
        objects = self.env[model].browse(active_ids)
        analytic_accounts = objects.mapped("analytic_account_ids")
        if self.bm_date_from and self.bm_date_to:
            analytics = analytic_accounts.filtered(
                lambda l: l.bm_date_to >= self.bm_date_from
                and l.bm_date_from <= self.bm_date_to
            )
        self.analytic_ids = analytics

    @api.model
    def default_get(self, default_fields):
        values = super().default_get(default_fields)
        model = self._context.get("active_model", False)
        active_ids = self._context.get("active_ids", False)
        # Check state confirmed on project
        if model == "res.project":
            projects = self.env[model].browse(active_ids)
            if any(project.state != "confirm" for project in projects):
                raise UserError(_("Project must be state Confirmed."))
            analytic_group_id = self.env.ref(
                "budget_res_project_department.analytic_group_project"
            )
        elif model == "hr.department":
            analytic_group_id = self.env.ref(
                "budget_res_project_department.analytic_group_department"
            )
        analytic_group = self.env["account.analytic.group"].browse(analytic_group_id.id)
        values["group_id"] = analytic_group.id
        return values

    def _get_value_object(self, obj):
        return {
            "name": obj.name,
            "code": obj.code,
            "group_id": self.group_id.id or False,
            "budget_period_id": self.budget_period_id.id,
            "bm_date_from": self.bm_date_from,
            "bm_date_to": self.bm_date_to,
            "auto_adjust_date_commit": self.auto_adjust_date_commit,
        }

    def _check_operating_unit(self, department, val):
        """Update operating unit in analytic, if there is field operating unit
        in department and analytic."""
        if (
            getattr(department, "operating_unit_id", "/") != "/"
            and getattr(self.env["account.analytic.account"], "operating_unit_ids", "/")
            != "/"
        ):
            operating_unit = department.operating_unit_id
            if not operating_unit:
                raise UserError(_("Department there is not operating unit"))
            val["operating_unit_ids"] = [(6, 0, [operating_unit.id])]
        return val

    def _prepare_analytic_vals(self, objects):
        self.ensure_one()
        analytic_accounts = objects.mapped("analytic_account_ids")
        analytic_vals = []
        field_model = DICT_FIELD_MODEL[objects._name]
        for obj in objects:
            existing_analytic = analytic_accounts.filtered(
                lambda l: l.id in self.analytic_ids.ids and l[field_model].id == obj.id
            )
            if existing_analytic:
                continue
            val = self._get_value_object(obj)
            if obj._name == "res.project":
                val["project_id"] = obj.id
                val = self._check_operating_unit(obj.department_id, val)
            elif obj._name == "hr.department":
                val["department_id"] = obj.id
                val = self._check_operating_unit(obj, val)
            analytic_vals.append(val)
        return analytic_vals

    def action_create_analytic(self):
        model = self._context.get("active_model", False)
        active_ids = self._context.get("active_ids", False)
        objects = self.env[model].browse(active_ids)
        analytic_vals = self._prepare_analytic_vals(objects)
        analytic = self.env["account.analytic.account"].create(analytic_vals)
        list_view = self.env.ref("budget_control.view_budget_analytic_list").id
        form_view = self.env.ref("budget_control.view_account_analytic_account_form").id
        return {
            "name": _("Analytic Accounts"),
            "type": "ir.actions.act_window",
            "res_model": "account.analytic.account",
            "views": [[list_view, "list"], [form_view, "form"]],
            "view_mode": "list",
            "domain": [("id", "in", analytic and analytic.ids or [])],
        }