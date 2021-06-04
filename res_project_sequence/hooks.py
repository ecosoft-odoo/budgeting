# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def assign_old_sequences(cr, registry):
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        project_obj = env["res.project"]
        sequence_obj = env["ir.sequence"]
        for project in project_obj.search([], order="id"):
            project.write({"code": sequence_obj.next_by_code("res.project")})
