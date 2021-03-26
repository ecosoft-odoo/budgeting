# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class FundConstraint(models.Model):
    _inherit = "fund.constraint"
    _rec_name = "number"

    number = fields.Char(required=True, default="/", readonly=True, copy=False)

    @api.model
    def create(self, vals):
        number = self.env["ir.sequence"].next_by_code("fund.constraint")
        vals["number"] = number
        return super().create(vals)

    def name_get(self):
        res = []
        for fc in self:
            name = fc.name
            if fc.number:
                name = "[{}] {}".format(fc.number, name)
            res.append((fc.id, name))
        return res

    @api.model
    def name_search(self, name, args=None, operator="ilike", limit=100):
        args = args or []
        domain = []
        if name:
            domain = [
                "|",
                ("number", operator, name),
                ("name", operator, name),
            ]
        fund_constraint = self.search(domain + args, limit=limit)
        return fund_constraint.name_get()
