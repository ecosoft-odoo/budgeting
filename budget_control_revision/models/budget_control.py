# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class BudgetControl(models.Model):
    _name = "budget.control"
    _inherit = ["budget.control", "base.revision"]
    _order = "revision_number desc, analytic_account_id"

    current_revision_id = fields.Many2one(
        comodel_name="budget.control",
    )
    old_revision_ids = fields.One2many(
        comodel_name="budget.control",
    )
    init_revision = fields.Boolean(
        default=True,
        readonly=True,
    )

    # Add budget_period_id for check constrains
    _sql_constraints = [
        (
            "revision_unique",
            "unique(unrevisioned_name, revision_number, budget_period_id)",
            "Reference and revision must be unique.",
        )
    ]

    def _filter_by_budget_control(self, val):
        res = super()._filter_by_budget_control(val)
        if val["amount_type"] != "1_budget":
            return res
        revision_number = (
            0 if not val["revision_number"] else int(val["revision_number"])
        )
        return res and revision_number == self.revision_number

    def _get_new_rev_data(self, new_rev_number):
        """Update revision budget control"""
        self.ensure_one()
        new_rev_dict = super()._get_new_rev_data(new_rev_number)
        new_rev_dict["init_revision"] = False
        return new_rev_dict

    def action_create_revision(self):
        if any(rec.state != "cancel" for rec in self):
            raise UserError(
                _(
                    "Budget control can only be revision when it is in the 'cancel' state."
                )
            )
        return self.create_revision()
