# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def assign_old_sequences(cr, registry):
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        budget_control_obj = env["budget.control"]
        sequence_obj = env["ir.sequence"]
        for fc in budget_control_obj.search([], order="id"):
            fc.write({"number": sequence_obj.next_by_code("budget.control")})
