# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BudgetControl(models.Model):
    _name = "budget.control"
    _inherit = ["budget.control", "tier.validation"]
    _state_from = ["submit"]
    _state_to = ["done"]

    _tier_validation_manual_config = False

    def _allow_to_remove_reviews(self, values):
        # Budget control uses "submit" as _state_from, so going back to
        # "draft" (e.g., reset to draft) is not covered by the default rule.
        # Extend it so reviews are cleared when the document is reset to draft.
        if values.get(self._state_field) == "draft":
            return True
        return super()._allow_to_remove_reviews(values)
