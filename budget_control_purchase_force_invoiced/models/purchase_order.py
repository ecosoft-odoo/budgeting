# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def write(self, vals):
        """force_invoiced on -> release remaining commit; off -> recompute it."""
        to_close = to_reopen = self.browse()
        if "force_invoiced" in vals:
            if vals["force_invoiced"]:
                to_close = self.filtered(lambda o: not o.force_invoiced)
            else:
                to_reopen = self.filtered(lambda o: o.force_invoiced)
        res = super().write(vals)
        to_close.close_budget_move()
        to_reopen.recompute_budget_move()
        return res
