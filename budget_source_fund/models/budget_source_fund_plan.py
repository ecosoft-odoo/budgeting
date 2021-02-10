# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class BudgetSourceFundPlan(models.Model):
    _name = "budget.source.fund.plan"
    _inherit = ["mail.thread"]
    _description = "Source of Fund Plan"

    name = fields.Char(
        string="Allocation",
        required=True,
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    fund_id = fields.Many2one(
        comodel_name="budget.source.fund",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    budget_period_id = fields.Many2one(
        comodel_name="budget.period",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    date_from = fields.Date(related="budget_period_id.bm_date_from")
    date_to = fields.Date(related="budget_period_id.bm_date_to")
    active = fields.Boolean(default=True)
    company_currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="fund_id.company_id.currency_id",
        string="Company Currency",
        readonly=True,
        help="Utility field to fund amount currency",
    )
    allocated_amount = fields.Monetary(
        default=0.0,
        currency_field="company_currency_id",
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        default="draft",
        tracking=True,
    )
    allocation_line = fields.One2many(
        comodel_name="budget.source.fund.allocation",
        inverse_name="allocation_id",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    def action_done(self):
        self.write({"state": "done"})
        return True

    def action_cancel(self):
        self.write({"state": "cancel"})
        return True

    def action_draft(self):
        self.write({"state": "draft"})
        return True

    @api.constrains("allocation_line")
    def _check_line_constrains(self):
        for rec in self:
            # check allocated amount
            total_amount = sum(rec.allocation_line.mapped("amount"))
            if (
                float_compare(
                    rec.allocated_amount,
                    total_amount,
                    precision_rounding=rec.company_currency_id.rounding,
                )
                != 0
            ):
                raise UserError(
                    _(
                        "Total allocated (%.2f) is not equal Allocated Amount (%.2f)"
                        % (total_amount, rec.allocated_amount)
                    )
                )
            # check date inside budget period
            date_from = (
                x for x in rec.allocation_line if x.date_from < rec.date_from
            )
            date_to = (
                x for x in rec.allocation_line if x.date_to > rec.date_to
            )
            if list(date_from) or list(date_to):
                raise UserError(_("date from or date to is overlaps."))

    @api.constrains("state")
    def _check_allocated_empty(self):
        for rec in self:
            if rec.state == "done" and not rec.allocation_line:
                raise UserError(_("You need to add a line before confirm."))
