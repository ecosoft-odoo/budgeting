# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class TierValidation(models.AbstractModel):
    _inherit = "tier.validation"

    check_budget = fields.Boolean(compute="_compute_check_budget")

    def _compute_check_budget(self):
        for rec in self:
            check_budget = rec.review_ids.filtered(
                lambda r: r.status == "pending" and (self.env.user in r.reviewer_ids)
            ).mapped("check_budget")
            rec.check_budget = True in check_budget

    def validate_tier(self):
        """Check budget before validate tier"""
        self.ensure_one()
        lines = getattr(self, "_docline_rel", None)
        line_type = getattr(self, "_docline_type", None)
        if self.check_budget and lines and line_type:
            # Special case advance clearing
            if getattr(self, "advance", False):
                line_type = "advance"
            self.env["budget.period"].check_budget_precommit(
                self[lines].sudo(), doc_type=line_type
            )
        return super().validate_tier()
