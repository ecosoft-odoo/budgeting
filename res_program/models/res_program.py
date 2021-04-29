# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResProgram(models.Model):
    _name = "res.program"
    _description = "Program"

    name = fields.Char(required=True)
    code = fields.Char()
    active = fields.Boolean(default=True)

    def name_get(self):
        res = []
        for program in self:
            name = program.name
            if program.code:
                name = "[{}] {}".format(program.code, name)
            res.append((program.id, name))
        return res

    @api.model
    def name_search(self, name, args=None, operator="ilike", limit=100):
        args = args or []
        domain = []
        if name:
            domain = ["|", ("code", operator, name), ("name", operator, name)]
        program = self.search(domain + args, limit=limit)
        return program.name_get()
