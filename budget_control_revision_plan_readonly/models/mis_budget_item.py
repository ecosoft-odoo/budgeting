# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MisBudgetItem(models.Model):
    _inherit = "mis.budget.item"

    is_readonly = fields.Boolean(compute="_compute_amount_readonly")

    @api.depends("budget_control_id")
    def _compute_amount_readonly(self, date=False):
        if not date:
            date = fields.Date.context_today(self)
        for rec in self:
            rec.is_readonly = False
            if (
                not rec.budget_control_id.init_revision
                and rec.date_from <= date
            ):
                rec.is_readonly = True

    @api.constrains("amount")
    def _check_amount_readonly(self):
        revision_number = self._context.get("revision_number", False)
        for rec in self:
            if not revision_number and rec.is_readonly:
                raise UserError(_("You can not edit past amount."))
