# Copyright 2021 Ecosoft Co., Ltd. (<http://ecosoft.co.th>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class BaseRevision(models.AbstractModel):
    _inherit = "base.revision"

    def _copy_item_ids(self, new_revision):
        old_items = self.item_ids
        for i, item in enumerate(new_revision.item_ids):
            item.update({"amount": old_items[i].amount})

    def _copy_revision_budget_control(self):
        ctx = self._context.copy()
        ctx.update(
            {
                "create_revision": True,
                "kpi_ids": self.item_ids.mapped(
                    "kpi_expression_id.kpi_id"
                ).ids,
            }
        )
        self.allocation_line.mapped("allocation_id").action_draft()
        new_revision = super(
            BaseRevision, self.with_context(ctx)
        ).copy_revision_with_context()
        self._copy_item_ids(new_revision)
        self.item_ids.write({"active": False})
        self.allocation_line.write({"active": False})
        return new_revision

    def copy_revision_with_context(self):
        model = self._context.get("active_model", False)
        if model and model == "budget.control":
            new_revision = self._copy_revision_budget_control()
        else:
            new_revision = super().copy_revision_with_context()
        return new_revision
