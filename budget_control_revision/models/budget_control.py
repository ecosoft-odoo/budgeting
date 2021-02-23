# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import ast

from odoo import fields, models


class BudgetControl(models.Model):
    _name = "budget.control"
    _inherit = ["budget.control", "base.revision"]

    current_revision_id = fields.Many2one(
        comodel_name="budget.control",
    )
    old_revision_ids = fields.One2many(
        comodel_name="budget.control",
    )
    revision_number = fields.Integer(readonly=True)

    _sql_constraints = [
        (
            "budget_control_uniq",
            "UNIQUE(budget_id, analytic_account_id, name)",
            "Duplicated analytic account for the same budget!",
        ),
    ]

    def _copy_item_ids(self, old_items):
        self.ensure_one()
        for i, item in enumerate(self.item_ids):
            item.update({"amount": old_items[i].amount})

    def _get_kpi_analytic(self):
        kpi_ids = list(
            map(
                lambda l: {
                    l.analytic_account_id.id: l.item_ids.mapped(
                        "kpi_expression_id.kpi_id"
                    ).ids
                },
                self,
            )
        )
        return kpi_ids

    def create_revision(self):
        """
        Step to create new revision:
        - Send context for auto create kpis from old revision.
            kpi_ids         : Used with module budget_control_selection
            create_revision : Create mis budget overlaps
        - Copy amount to new revision.
        - Inactive old item_ids, For report monitoring not duplicated.
        """
        ctx = self._context.copy()
        kpi_ids = self._get_kpi_analytic()
        ctx.update(
            {
                "create_revision": True,
                "kpi_ids": kpi_ids,
            }
        )
        res = super(BudgetControl, self.with_context(ctx)).create_revision()
        domain = ast.literal_eval(res.get("domain", False))
        new_bc_ids = self.browse(domain[0][2])
        # loop case multi
        for rec in new_bc_ids:
            old_lastest = rec.old_revision_ids[0]
            old_items = old_lastest.item_ids
            if old_items:
                rec._copy_item_ids(old_items)
                old_items.write({"active": False})
        return res
