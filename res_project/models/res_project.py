# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ResProject(models.Model):
    _name = "res.project"
    _inherit = "mail.thread"
    _description = "Project Management"
    _check_company_auto = True
    _rec_name = "code"
    _rec_names_search = ["code", "name"]

    name = fields.Char(
        required=True,
        tracking=True,
    )
    code = fields.Char(
        tracking=True,
    )
    parent_project_id = fields.Many2one(
        comodel_name="res.project",
        string="Parent",
        tracking=True,
    )
    parent_project_name = fields.Char(
        compute="_compute_parent_project_name",
        string="Parent Project",
        store=True,
        readonly=False,
        tracking=True,
    )
    child_ids = fields.One2many(
        comodel_name="res.project",
        inverse_name="parent_project_id",
        string="Child Projects",
        check_company=True,
    )
    active = fields.Boolean(
        default=True,
        tracking=True,
        help="If the active field is set to False, "
        "it will allow you to hide the project without removing it.",
    )
    description = fields.Html(copy=False)
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
    )
    project_manager_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Project Manager",
        tracking=True,
    )
    date_from = fields.Date(
        required=True,
        string="Project Start",
        tracking=True,
    )
    date_to = fields.Date(
        required=True,
        string="Project End",
        tracking=True,
    )
    department_id = fields.Many2one(
        comodel_name="hr.department",
        required=True,
    )
    member_ids = fields.Many2many(
        comodel_name="hr.employee.public",
        relation="project_employee_rel",
        column1="project_id",
        column2="employee_id",
        string="Member",
    )
    plan_amount = fields.Monetary(
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
    amount = fields.Monetary()
    code = fields.Char(required=True, default="/", readonly=True, copy=False)
    next_split = fields.Integer(string="Next split code", default=1)

    _sql_constraints = [("unique_name", "UNIQUE(name)", "name must be unique")]

    @api.depends("parent_project_id", "name")
    def _compute_parent_project_name(self):
        for rec in self:
            rec.parent_project_name = (
                rec.parent_project_id and rec.parent_project_id.name or rec.name
            )

    @api.depends("project_plan_ids")
    def _compute_plan_amount(self):
        for rec in self:
            rec.plan_amount = sum(rec.project_plan_ids.mapped("amount"))

    @api.model_create_multi
    def create(self, vals_list):
        """
        Sequence will run 2 method
        - Split project: use the same code parent project and add subcode
            Example: Project A has code A00001.
            when split project A, it will A00001-1, next split is A00001-2
        - Create new project: use new sequence
        - Has code already: skip it
        """
        for vals in vals_list:
            if not vals.get("parent_project_id", False):
                vals["parent_project_name"] = vals["name"]

            if vals.get("code", "/") == "/":
                split_project = self._context.get("split_project", False)
                parent_project_id = vals.get(
                    "parent_project_id", False
                ) or self._context.get("parent_project_id", False)
                import_file = self._context.get("import_file", False)
                # Split project or import with parent
                if split_project or (import_file and parent_project_id):
                    parent_project = self.env["res.project"].browse(parent_project_id)
                    if parent_project:
                        next_split = parent_project.next_split
                        code = f"{parent_project.code}-{next_split}"
                        parent_project.write({"next_split": next_split + 1})
                else:
                    code = self.env["ir.sequence"].next_by_code("res.project")
                vals["code"] = code

        return super().create(vals)

    @api.depends("code", "name")
    def _compute_display_name(self):
        for project in self:
            name = project.name
            if project.code:
                name = f"[{project.code}] {name}"
            project.display_name = name

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
                "default_parent_project_id": project.parent_project_id.id or project.id,
                "default_parent_project_name": project.parent_project_name,
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
        date = self._context.get("force_project_date") or fields.Date.context_today(
            self
        )
        domain = [("date_to", "<", date), ("state", "=", "confirm")]
        return domain

    def action_auto_expired(self):
        """Close a project automatically when the specified conditions are met"""
        domain = self._get_domain_project_expired()
        project_expired = self.search(domain)
        return project_expired.action_close_project()

    @api.onchange("project_manager_id")
    def _onchange_department_id(self):
        for rec in self:
            rec.department_id = rec.project_manager_id.department_id or False
