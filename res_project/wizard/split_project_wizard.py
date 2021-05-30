# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models


class SplitProjectWizard(models.TransientModel):
    _name = "split.project.wizard"
    _description = "Split Project Wizard"

    parent_project = fields.Char(readonly=True)
    department_id = fields.Many2one(
        string="Department",
        comodel_name="hr.department",
        readonly=True,
    )
    date_from = fields.Date(string="Project Start", readonly=True)
    date_to = fields.Date(string="Project End", readonly=True)
    line_ids = fields.One2many(
        string="Lines",
        comodel_name="split.project.wizard.line",
        inverse_name="wizard_id",
    )

    def split_project(self):
        self.ensure_one()
        ResProject = self.env["res.project"]
        # Create new project record
        vals = [line._prepare_project_val() for line in self.line_ids]
        projects = ResProject.create(vals)
        # Delete parent project record
        parent_project = ResProject.search(
            [("name", "=", self.parent_project)]
        )
        if parent_project:
            parent_project.unlink()
        return {
            "name": _("Project"),
            "type": "ir.actions.act_window",
            "res_model": "res.project",
            "view_mode": "tree,form",
            "context": self.env.context,
            "domain": [("id", "in", projects.ids)],
        }


class SplitProjectWizardLine(models.TransientModel):
    _name = "split.project.wizard.line"
    _description = "Split Project Wizard Line"

    wizard_id = fields.Many2one(comodel_name="split.project.wizard")
    project_name = fields.Char(string="Project Name")

    def _prepare_project_val(self):
        self.ensure_one()
        return {
            "name": self.project_name,
            "parent_project": self.wizard_id.parent_project,
            "date_from": self.wizard_id.date_from,
            "date_to": self.wizard_id.date_to,
            "department_id": self.wizard_id.department_id.id,
            "company_id": self.env.company.id,
        }
