# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def _init_docline_budget_vals(self, budget_vals):
        self.ensure_one()
        budget_vals["is_agreement"] = self.order_id.po_type == "agreement"
        return super()._init_docline_budget_vals(budget_vals)
