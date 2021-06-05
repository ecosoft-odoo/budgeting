# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, models
from odoo.exceptions import UserError


class BudgetTransferItem(models.Model):
    _inherit = "budget.transfer.item"

    def _check_constraint_transfer(self):
        super()._check_constraint_transfer()
        analytic_tag = (
            self.source_analytic_tag_ids + self.target_analytic_tag_ids
        )
        dimension_constraints = analytic_tag.mapped(
            "analytic_dimension_id"
        ).filtered(lambda l: l.budget_transfer_constraint)
        for dimension in dimension_constraints:
            tags = analytic_tag.filtered(
                lambda l: l.analytic_dimension_id.id == dimension.id
            )
            source_analytic_tag = self.source_analytic_tag_ids.filtered(
                lambda l: l.analytic_dimension_id.id == dimension.id
            )
            cross_transfer_constraint = (
                source_analytic_tag.analytic_tag_constraint_ids
            )
            can_transfer = tags.filtered(
                lambda l: l.id == cross_transfer_constraint.id
            )
            if can_transfer:
                continue
            if len(set(tags.ids)) != 1:
                raise UserError(
                    _(
                        "Can not transfer because dimension '{}' is "
                        "not same analytic tag.".format(dimension.name)
                    )
                )
