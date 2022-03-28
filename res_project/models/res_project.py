# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ResProject(models.Model):
    _name = "res.project"
    _description = "Project Management"
    _inherit = "mail.thread"
    _check_company_auto = True

    name = fields.Char(
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
    )
    code = fields.Char(
        readonly=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
    )
    parent_project_id = fields.Many2one(
        comodel_name="res.project",
        string="Parent",
        readonly=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
    )
    parent_project = fields.Char(
        comodel_name="res.project",
        related="parent_project_id.name",
        string="Parent Project",
        store=True,
        readonly=False,
        tracking=True,
    )
    active = fields.Boolean(
        default=True,
        tracking=True,
        help="If the active field is set to False, "
        "it will allow you to hide the project without removing it.",
    )
    description = fields.Html(
        readonly=True, copy=False, states={"draft": [("readonly", False)]}
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        required=True,
        related="company_id.currency_id",
        states={"done": [("readonly", True)]},
    )
    project_manager_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Project Manager",
        readonly=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
    )
    date_from = fields.Date(
        required=True,
        string="Project Start",
        readonly=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
    )
    date_to = fields.Date(
        required=True,
        string="Project End",
        readonly=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
    )
    department_id = fields.Many2one(
        comodel_name="hr.department",
        readonly=True,
        required=True,
        states={"draft": [("readonly", False)]},
    )
    member_ids = fields.Many2many(
        comodel_name="hr.employee.public",
        relation="project_employee_rel",
        column1="project_id",
        column2="employee_id",
        string="Member",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    plan_amount = fields.Monetary(
        string="Plan Amount",
        compute="_compute_plan_amount",
        currency_field="currency_id",
        help="Total Plan Amount for this project",
    )
    project_plan_ids = fields.One2many(
        comodel_name="res.project.plan",
        inverse_name="project_id",
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirm", "Confirmed"),
            ("close", "Closed"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
        default="draft",
    )

    _sql_constraints = [("unique_name", "UNIQUE(name)", "name must be unique")]

    @api.depends("project_plan_ids")
    def _compute_plan_amount(self):
        for rec in self:
            rec.plan_amount = sum(rec.project_plan_ids.mapped("amount"))

    @api.model
    def create(self, vals):
        if not vals.get("parent_project_id", False):
            vals["parent_project"] = vals["name"]
        return super().create(vals)

    @api.model
    def name_search(self, name, args=None, operator="ilike", limit=100):
        args = args or []
        domain = []
        if name:
            domain = ["|", ("code", operator, name), ("name", operator, name)]
        projects = self.search(domain + args, limit=limit)
        return projects.name_get()

    def name_get(self):
        res = []
        for project in self:
            name = project.name
            if project.code:
                name = "[{}] {}".format(project.code, name)
            res.append((project.id, name))
        return res

    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {}, name=_("%s (copy)") % self.name)
        return super().copy(default)

    def action_split_project(self):
        project = self.browse(self.env.context["active_ids"])
        if len(project) != 1:
            raise UserError(_("Please select one project."))
        wizard = self.env.ref("res_project.split_project_wizard_form")
        return {
            "name": _("Split Project"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "split.project.wizard",
            "views": [(wizard.id, "form")],
            "view_id": wizard.id,
            "target": "new",
            "context": {
                "default_parent_project_id": project.parent_project_id
                and project.parent_project_id.id
                or project.id,
                "default_parent_project": project.parent_project,
                "default_date_from": project.date_from,
                "default_date_to": project.date_to,
                "default_project_manager_id": project.project_manager_id.id,
                "default_department_id": project.department_id.id,
                "default_member_ids": [(6, 0, project.member_ids.ids)],
            },
        }

    def action_confirm(self):
        return self.write({"state": "confirm"})

    def action_close_project(self):
        return self.write({"state": "close"})

    def action_draft(self):
        return self.write({"state": "draft"})

    def action_cancel(self):
        return self.write({"state": "cancel"})

    def _get_domain_project_expired(self):
        date = self._context.get(
            "force_project_date"
        ) or fields.Date.context_today(self)
        domain = [("date_to", "<", date), ("state", "=", "confirm")]
        return domain

    def action_auto_expired(self):
        domain = self._get_domain_project_expired()
        project_expired = self.search(domain)
        if not project_expired:
            return
        return project_expired.write({"active": False})

    @api.onchange("project_manager_id")
    def _onchange_department_id(self):
        for rec in self:
            rec.department_id = rec.project_manager_id.department_id or False
