# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
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
        compute="_compute_init_revision",
        store=True,
    )

    # Add budget_period_id and analytic account for check constrains
    _sql_constraints = [
        (
            "revision_unique",
            "unique(\
                unrevisioned_name, \
                revision_number, \
                budget_period_id, \
                analytic_account_id\
            )",
            "Reference and revision must be unique.",
        )
    ]

    @api.depends("revision_number")
    def _compute_init_revision(self):
        for rec in self:
            rec.init_revision = not rec.revision_number

    def _filter_by_budget_control(self, val):
        res = super()._filter_by_budget_control(val)
        if val["amount_type"] != "10_budget":
            return res
        revision_number = (
            0 if not val["revision_number"] else int(val["revision_number"])
        )
        return res and revision_number == self.revision_number

    def action_create_revision(self):
        if any(rec.state != "cancel" for rec in self):
            raise UserError(
                self.env._(
                    "Budget control can only be revision "
                    "when it is in the 'cancel' state."
                )
            )
        return self.create_revision()
