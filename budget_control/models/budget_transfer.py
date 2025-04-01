# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare


class BudgetTransfer(models.Model):
    _name = "budget.transfer"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Budget Transfer"

    name = fields.Char(
        default="/",
        index=True,
        copy=False,
        required=True,
    )
    budget_period_id = fields.Many2one(
        comodel_name="budget.period",
        default=lambda self: self.env["budget.period"]._get_eligible_budget_period(),
        required=True,
    )
    transfer_item_ids = fields.One2many(
        comodel_name="budget.transfer.item",
        inverse_name="transfer_id",
        copy=True,
    )
    company_ids = fields.Many2many(
        comodel_name="res.company",
        relation="budget_transfer_company_rel",
        column1="budget_transfer_id",
        column2="company_id",
        compute="_compute_company_ids",
        store=True,
        string="Companies",
        tracking=True,
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submit", "Submitted"),
            ("transfer", "Transferred"),
            ("reverse", "Reversed"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        default="draft",
        tracking=True,
    )

    @api.depends("transfer_item_ids")
    def _compute_company_ids(self):
        for rec in self:
            bc_from = rec.transfer_item_ids.mapped("budget_control_from_id")
            bc_to = rec.transfer_item_ids.mapped("budget_control_to_id")
            rec.company_ids = (bc_from + bc_to).company_ids

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("budget.transfer") or "/"
                )
        return super().create(vals_list)

    def unlink(self):
        """Check state draft can delete only."""
        if any(rec.state != "draft" for rec in self):
            raise UserError(
                self.env._(
                    "You are trying to delete a record that is still referenced!"
                )
            )
        return super().unlink()

    def action_cancel(self):
        return self.write({"state": "cancel"})

    def action_submit(self):
        item_ids = self.mapped("transfer_item_ids")
        if not item_ids:
            raise UserError(self.env._("You need to add a line before submit."))

        for transfer in item_ids:
            transfer._check_constraint_transfer()
        return self.write({"state": "submit"})

    def action_transfer(self):
        self.mapped("transfer_item_ids").transfer()
        self._check_budget_control()
        return self.write({"state": "transfer"})

    def action_reverse(self):
        self.mapped("transfer_item_ids").reverse()
        self._check_budget_control()
        return self.write({"state": "reverse"})

    def _check_budget_available_analytic(self, budget_controls):
        BudgetPeriod = self.env["budget.period"]
        for budget_ctrl in budget_controls:
            query_data = BudgetPeriod._get_budget_avaiable(
                budget_ctrl.analytic_account_id.id, budget_ctrl.template_line_ids
            )
            balance = sum(q["amount"] for q in query_data if q["amount"] is not None)
            if (
                float_compare(
                    balance,
                    0.0,
                    precision_rounding=budget_ctrl.currency_id.rounding,
                )
                == -1
            ):
                raise ValidationError(
                    self.env._(
                        "This transfer will result in negative budget balance for %s"
                    )
                    % budget_ctrl.name
                )
        return True

    def _check_budget_control(self):
        """Ensure no budget control will result in negative balance."""
        transfers = self.mapped("transfer_item_ids")
        budget_controls = transfers.mapped("budget_control_from_id") | transfers.mapped(
            "budget_control_to_id"
        )
        # Control all analytic
        self._check_budget_available_analytic(budget_controls)
