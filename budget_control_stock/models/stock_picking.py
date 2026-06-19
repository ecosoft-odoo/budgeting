# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"
    _docline_rel = "move_ids"
    _docline_type = "stock"

    budget_move_ids = fields.One2many(
        comodel_name="stock.budget.move",
        inverse_name="picking_id",
    )

    def recompute_budget_move(self):
        self.mapped("move_ids").recompute_budget_move()

    def close_budget_move(self):
        self.mapped("move_ids").close_budget_move()

    def write(self, vals):
        """
        Uncommit the budget when the document state changes.
        If the picking is canceled or moved to draft (ready),
        all budget commitments will be deleted.

        State transitions:
            - "done"   = Validated (stock.move is done)
            - "cancel" = Cancelled
        """
        res = super().write(vals)
        if vals.get("state") in ("done", "cancel", "draft"):
            doclines = self.mapped("move_ids")
            if vals.get("state") in ("cancel", "draft"):
                doclines.write({"date_commit": False})
            doclines.recompute_budget_move()
        if "move_ids" in vals or "move_ids_without_package" in vals:
            BudgetPeriod = self.env["budget.period"]
            for doc in self:
                if doc.state not in ("cancel", "draft"):
                    doc.recompute_budget_move()
                    BudgetPeriod.check_budget(doc.move_ids, doc_type="stock")
        return res

    def unlink(self):
        self.move_ids.budget_move_ids.unlink()
        return super().unlink()

    def action_cancel(self):
        res = super().action_cancel()
        for doc in self:
            doclines = doc.move_ids
            doclines.write({"date_commit": False})
            doclines.recompute_budget_move()
        return res

    def button_validate(self):
        res = super().button_validate()
        BudgetPeriod = self.env["budget.period"]
        for doc in self:
            BudgetPeriod.check_budget(doc.move_ids, doc_type="stock")
        return res

    def action_confirm(self):
        res = super().action_confirm()
        BudgetPeriod = self.env["budget.period"]
        for doc in self:
            doc.recompute_budget_move()
            BudgetPeriod.check_budget(doc.move_ids, doc_type="stock")
        return res

    def action_assign(self):
        res = super().action_assign()
        BudgetPeriod = self.env["budget.period"]
        budget_pickings = self.filtered(lambda p: p.picking_type_id.budget_commit)
        for doc in budget_pickings:
            doc.recompute_budget_move()
            BudgetPeriod.check_budget(doc.move_ids, doc_type="stock")
        return res

    def do_unreserve(self):
        res = super().do_unreserve()
        budget_pickings = self.filtered(lambda p: p.picking_type_id.budget_commit)
        for doc in budget_pickings:
            doc.recompute_budget_move()
        return res
