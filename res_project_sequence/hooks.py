# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def assign_old_sequences(cr, registry):
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        project_obj = env["res.project"]
        sequence_obj = env["ir.sequence"]
        for project in project_obj.search([], order="id"):
            if project.parent_project_id:
                parent_project = project.parent_project_id
                next_split = parent_project.next_split
                code = "{}-{}".format(parent_project.code, next_split)
                project.write({"code": code})
                parent_project.write({"next_split": next_split + 1})
            else:
                project.write(
                    {"code": sequence_obj.next_by_code("res.project")}
                )
