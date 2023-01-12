# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResProject(models.Model):
    _inherit = "res.project"
    _rec_name = "code"

    code = fields.Char(required=True, default="/", readonly=True, copy=False)
    next_split = fields.Integer(string="Next split code", default=1)

    @api.model
    def create(self, vals):
        """
        Sequence will run 2 method
        - Split project: use the same code parent project and add subcode
            Example: Project A has code A00001.
            when split project A, it will A00001-1, next split is A00001-2
        - Create new project: use new sequence
        - Has code already: skip it
        """
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
                    code = "{}-{}".format(parent_project.code, next_split)
                    parent_project.write({"next_split": next_split + 1})
            else:
                code = self.env["ir.sequence"].next_by_code("res.project")
            vals["code"] = code
        return super().create(vals)
