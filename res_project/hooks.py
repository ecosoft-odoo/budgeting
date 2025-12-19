# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, _, api
from odoo.exceptions import UserError


def generate_code_from_parent(parent_project):
    """generate code for project from its parent's code"""
    next_split = parent_project.next_split
    code = f"{parent_project.code}-{next_split}"
    parent_project.write({"next_split": next_split + 1})
    return code


def check_recursive_project(project):
    """Check if project has a recursive parent"""
    parent_project = project
    project_list = []
    while parent_project.parent_project_id:
        if project.id in project_list:
            raise UserError(
                _(
                    "Please check 'Parent Project' in project '{}' "
                    "must not be recursive."
                ).format(project.name)
            )
        project_list.append(parent_project.parent_project_id.id)
        parent_project = parent_project.parent_project_id


def assign_new_sequences(cr, registry):
    """Assign new sequences to projects"""
    env = api.Environment(cr, SUPERUSER_ID, {})
    project_obj = env["res.project"]
    sequence_obj = env["ir.sequence"]
    projects = project_obj.with_context(active_test=False).search([], order="id")
    for project in projects:
        check_recursive_project(project)
        parent_project = project.parent_project_id
        # Skip it, if project is parent and has code already
        if parent_project and parent_project.code != "/":
            code = generate_code_from_parent(parent_project)
            project.write({"code": code})
        elif project.code == "/":
            project.write({"code": sequence_obj.next_by_code("res.project")})
