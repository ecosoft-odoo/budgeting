# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class BudgetControl(models.Model):
    _inherit = "budget.control"

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        compute="_compute_budget_operating_unit",
        store=True,
    )

    @api.depends("analytic_account_id.operating_unit_ids")
    def _compute_budget_operating_unit(self):
        """Operating Unit can selected 1 only for analytic account"""
        for rec in self:
            if len(rec.analytic_account_id.operating_unit_ids) > 1:
                raise UserError(_("Analytic Account can't select operating unit > 1"))
            rec.operating_unit_id = rec.analytic_account_id.operating_unit_ids.id

    def check_budget_transfer_permission(self):
        # Transfer
        transfer_budget_from = self.env.context.get("transfer_budget_from", False)
        transfer_budget_to = self.env.context.get("transfer_budget_to", False)
        # Group Access All
        access_all_budget_from = self.user_has_groups(
            "budget_control_operating_unit.group_access_all_ou_transfer_from"
        )
        access_all_budget_to = self.user_has_groups(
            "budget_control_operating_unit.group_access_all_ou_transfer_to"
        )
        # Has permission for budget transfer
        budget_transfer = self._context.get("budget_transfer_access_sudo", False)
        tier_validation = self._context.get("from_review_systray", False)
        # Check condition,
        # Budget Transfer or has access all transfer or Tier Validation (if install)
        if (
            (transfer_budget_from and access_all_budget_from)
            or (transfer_budget_to and access_all_budget_to)
            or budget_transfer
            or tier_validation
        ):
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
            self = self.sudo().with_context(force_all_ou=1)
        return super().search(args, offset, limit, order, count)

    def _read(self, fields):
        if self.check_budget_transfer_permission():
            self = self.sudo()
        return super()._read(fields)

    def _get_context_monitoring(self):
        ctx = super()._get_context_monitoring()
        # Check module budget_control_tier_validation is installed,
        # it will allow user approve can see data monitoring.
        if hasattr(self, "review_ids") and self.env.user in self.mapped(
            "review_ids.reviewer_ids"
        ):
            ctx["force_all_ou"] = 1
        return ctx
