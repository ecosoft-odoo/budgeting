# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from odoo import api, fields, models


class BudgetControl(models.Model):
    _inherit = "budget.control"

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        compute="_compute_budget_operating_unit",
        store=True,
    )

    @api.depends("analytic_account_id")
    def _compute_budget_operating_unit(self):
        for rec in self:
            if len(rec.analytic_account_id.operating_unit_ids) == 1:
                rec.operating_unit_id = rec.analytic_account_id.operating_unit_ids.id

    def check_budget_transfer_permission(self):
        source_budget_all_ou = self.env.user.company_id.budget_transfer_source_all_ou
        target_budget_all_ou = self.env.user.company_id.budget_transfer_target_all_ou
        if (
            (self._context.get("source_budget", False) and source_budget_all_ou)
            or (self._context.get("target_budget", False) and target_budget_all_ou)
            or self._context.get("access_sudo", False)
            or self._context.get("from_review_systray", False)
        ):  # support with tier validation
            return True
        return False

    @api.model
    def name_search(self, name, args=None, operator="ilike", limit=100):
        if self.check_budget_transfer_permission():
            self = self.sudo()
        return super().name_search(name, args, operator, limit)

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        """Search more -> show all OU"""
        if self.check_budget_transfer_permission():
            self = self.sudo()
            self.with_context(force_all_ou=1)
        return super().search(args, offset, limit, order, count)

    def _read(self, fields):
        if self.check_budget_transfer_permission():
            self = self.sudo()
        return super()._read(fields)
