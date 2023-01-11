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

    def _get_computed_account(self):
        self.ensure_one()
        if self.activity_id and not self._is_realtime_inventory_product():
            return self.activity_id.account_id
        return super()._get_computed_account()

    def _prepare_analytic_line(self):
        res = super()._prepare_analytic_line()
        for i, ml in enumerate(self):
            res[i]["activity_id"] = ml.activity_id.id
        return res

    @api.onchange("activity_id")
    def _onchange_activity_id(self):
        if self.activity_id:
            self.account_id = self.activity_id.account_id
