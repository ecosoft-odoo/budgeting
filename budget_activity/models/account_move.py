# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    activity_id = fields.Many2one(
        comodel_name="budget.activity",
        string="Activity",
        index=True,
    )

    def _is_realtime_inventory_product(self):
        # Case non-realtime inventory product
        # activity's account takes priority over product's account
        if self.product_id.type != "product":
            return False
        if not hasattr(self.product_id.categ_id, "property_valuation"):
            return False
        return self.product_id.categ_id.property_valuation == "real_time"

    def _compute_account_id(self):
        """In case of Realtime Inventory Product,
        activity's account takes priority"""
        input_lines = self.filtered(
            lambda line: (
                line._is_realtime_inventory_product()
                and line.move_id.company_id.anglo_saxon_accounting
            )
        ).with_prefetch(
            ["move_id", "move_id.company_id", "move_id.journal_id.company_id"]
        )
        for line in input_lines:
            line = line.with_company(line.move_id.journal_id.company_id)
            if line.activity_id:
                line.account_id = line.activity_id.account_id
        return super(AccountMoveLine, self - input_lines)._compute_account_id()

    def _prepare_analytic_lines(self):
        """Add activity_id to analytic line"""
        analytic_line_vals = super()._prepare_analytic_lines()
        self.ensure_one()
        if self.activity_id:  # Check if activity_id is set
            for analytic_line in analytic_line_vals:
                analytic_line["activity_id"] = self.activity_id.id
        return analytic_line_vals

    @api.onchange("activity_id")
    def _onchange_activity_id(self):
        if self.activity_id:
            self.account_id = self.activity_id.account_id
