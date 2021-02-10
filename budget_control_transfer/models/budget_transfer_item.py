# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class BudgetTransferItem(models.Model):
    _name = "budget.transfer.item"
    _description = "Budget Transfer by Item"

    transfer_id = fields.Many2one(
        comodel_name="budget.transfer",
        ondelete="cascade",
        index=True,
    )
    mis_budget_id = fields.Many2one(
        comodel_name="mis.budget",
        related="transfer_id.mis_budget_id",
    )
    source_budget_control_id = fields.Many2one(
        comodel_name="budget.control",
        string="Source",
        domain="[('budget_id', '=', mis_budget_id)]",
        required=True,
        index=True,
    )
    target_budget_control_id = fields.Many2one(
        comodel_name="budget.control",
        string="Target",
        domain="[('budget_id', '=', mis_budget_id)]",
        required=True,
        index=True,
    )
    source_item_id = fields.Many2one(
        comodel_name="mis.budget.item",
        domain="[('budget_control_id', '=', source_budget_control_id)]",
        ondelete="restrict",
        index=True,
    )
    target_item_id = fields.Many2one(
        comodel_name="mis.budget.item",
        domain="[('budget_control_id', '=', target_budget_control_id)]",
        ondelete="restrict",
        index=True,
    )
    source_amount = fields.Float(
        string="Source Amount",
        related="source_item_id.amount",
        readonly=True,
    )
    source_amount_available = fields.Float(
        compute="_compute_amount_available",
        readonly=True,
    )
    target_amount = fields.Float(
        string="Target Amount",
        related="target_item_id.amount",
        readonly=True,
    )
    target_amount_available = fields.Float(
        compute="_compute_amount_available",
        readonly=True,
    )
    amount = fields.Float(
        string="Transfer Amount",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("transfer", "Transferred"),
            ("reverse", "Reversed"),
        ],
        string="Status",
        default="draft",
    )

    def _get_budget_balance(self, budget_ctrl, kpi_name):
        balance = budget_ctrl and budget_ctrl.get_report_amount(
            [kpi_name], ["Available"]
        )
        return balance

    @api.depends("source_item_id", "target_item_id")
    def _compute_amount_available(self):
        for transfer in self:
            source_budget_ctrl = transfer.source_budget_control_id
            target_budget_ctrl = transfer.target_budget_control_id
            source_balance = self._get_budget_balance(
                source_budget_ctrl,
                transfer.source_item_id.kpi_expression_id.kpi_id.name,
            )
            target_balance = self._get_budget_balance(
                target_budget_ctrl,
                transfer.target_item_id.kpi_expression_id.kpi_id.name,
            )
            transfer.source_amount_available = source_balance
            transfer.target_amount_available = target_balance

    @api.onchange("source_budget_control_id")
    def _onchange_source_budget_control_id(self):
        self.source_item_id = False

    @api.onchange("target_budget_control_id")
    def _onchange_target_budget_control_id(self):
        self.target_item_id = False

    def transfer(self):
        for transfer in self:
            if transfer.state != "draft":
                raise ValidationError(_("Invalid state!"))
            if (
                transfer.source_budget_control_id
                == transfer.target_budget_control_id
            ):
                raise UserError(
                    _(
                        "You can not transfer from the same budget control sheet!"
                    )
                )
            if transfer.amount < 0.0:
                raise UserError(_("Transfer amount must be positive!"))
            transfer.source_item_id.amount -= transfer.amount
            transfer.target_item_id.amount += transfer.amount
            transfer.state = "transfer"
        # Final check
        source_amounts = self.mapped("source_item_id").mapped("amount")
        if list(filter(lambda a: a < 0, source_amounts)):
            raise ValidationError(_("Negative source amount after transfer!"))

    def reverse(self):
        for transfer in self:
            if transfer.state != "transfer":
                raise ValidationError(_("Invalid state!"))
            transfer.source_item_id.amount += transfer.amount
            transfer.target_item_id.amount -= transfer.amount
            transfer.state = "reverse"
