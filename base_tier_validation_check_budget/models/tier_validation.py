# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class TierValidation(models.AbstractModel):
    _inherit = "tier.validation"

    check_budget = fields.Boolean(compute="_compute_check_budget")

    def _compute_check_budget(self):
        for rec in self:
            check_budget = rec.review_ids.filtered(
                lambda r: r.status in ("waiting", "pending")
                and (self.env.user in r.reviewer_ids)
            ).mapped("check_budget")
            rec.check_budget = True in check_budget

    def validate_tier(self):
        """Check budget before validate tier"""
        self.ensure_one()
        lines = getattr(self, "_docline_rel", None)
        line_type = getattr(self, "_docline_type", None)

        # Check budget, if model has budget
        if self.check_budget and lines and line_type:
            doclines = self[lines].sudo()
            # Special case advance clearing
            if getattr(self, "advance", False):
                line_type = "advance"
            # --
            if self._name == "account.move" and self.move_type in (
                "in_invoice",
                "in_refund",
            ):
                doclines = self["invoice_line_ids"].sudo()
            self.env["budget.period"].check_budget_precommit(
                doclines, doc_type=line_type
            )
        return super().validate_tier()
