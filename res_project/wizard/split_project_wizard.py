# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class SplitProjectWizard(models.TransientModel):
    _name = "split.project.wizard"
    _description = "Split Project Wizard"

    parent_project_id = fields.Many2one(
        comodel_name="res.project",
        string="Parent",
        readonly=True,
    )
    parent_project_name = fields.Char(
        string="Parent Project",
        readonly=True,
    )
    project_manager_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Project Manager",
        readonly=True,
    )
    department_id = fields.Many2one(
        comodel_name="hr.department",
        string="Department",
        readonly=True,
    )
    date_from = fields.Date(string="Project Start", readonly=True)
    date_to = fields.Date(string="Project End", readonly=True)
    member_ids = fields.Many2many(
        comodel_name="hr.employee",
        string="Member",
        readonly=True,
    )
    line_ids = fields.One2many(
        string="Lines",
        comodel_name="split.project.wizard.line",
        inverse_name="wizard_id",
    )

    def split_project(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("Please add a new project name"))
        ResProject = self.env["res.project"]
        ctx = self._context.copy()
        if self.parent_project_id:
            # Archive parent project record
            self.parent_project_id.action_archive()
            # Update context
            ctx.update(
                {
                    "split_project": True,
                    "parent_project_id": self.parent_project_id.id,
                }
            )
        # Create new project record
        vals = [line._prepare_project_val() for line in self.line_ids]
        new_projects = ResProject.with_context(ctx).create(vals)
        return {
            "name": _("Project"),
            "type": "ir.actions.act_window",
            "res_model": "res.project",
            "view_mode": "tree,form",
            "context": self.env.context,
            "domain": [("id", "in", new_projects.ids)],
        }


class SplitProjectWizardLine(models.TransientModel):
    _name = "split.project.wizard.line"
    _description = "Split Project Wizard Line"

    wizard_id = fields.Many2one(comodel_name="split.project.wizard")
    project_name = fields.Char(string="Project Name")

    def _prepare_project_val(self):
        self.ensure_one()
        wizard = self.wizard_id
        return {
            "name": self.project_name,
            "parent_project_id": wizard.parent_project_id.id,
            "parent_project_name": wizard.parent_project_name,
            "date_from": wizard.date_from,
            "date_to": wizard.date_to,
            "project_manager_id": wizard.project_manager_id.id,
            "department_id": wizard.department_id.id,
            "company_id": self.env.company.id,
            "member_ids": [(6, 0, wizard.member_ids.ids)],
        }
