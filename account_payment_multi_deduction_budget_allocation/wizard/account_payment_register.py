# Copyright 2023 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models


class AccountPaymentRegister(models.TransientModel):
    _name = "account.payment.register"
    _inherit = [
        "analytic.dimension.line",
        "account.payment.register",
    ]
    _analytic_tag_field_name = "writeoff_analytic_tag_ids"

    writeoff_fund_id = fields.Many2one(
        comodel_name="budget.source.fund",
        string="Fund",
        index=True,
        tracking=True,
        ondelete="restrict",
        domain="[('id', 'in', writeoff_fund_all)]",
    )
    writeoff_fund_all = fields.Many2many(
        comodel_name="budget.source.fund",
    )
    writeoff_analytic_tag_all = fields.Many2many(
        comodel_name="account.analytic.tag",
        relation="account_payment_register_tag_all_rel",
        column1="register_id",
        column2="tag_all_id",
    )

    @api.onchange("writeoff_analytic_account_id")
    def _onchange_budget_all(self):
        for rec in self:
            allocation_lines = rec.writeoff_analytic_account_id.allocation_line_ids
            rec.writeoff_fund_all = allocation_lines.mapped("fund_id")
            rec.writeoff_fund_id = (
                rec.writeoff_fund_all._origin.id
                if len(rec.writeoff_fund_all) == 1
                else False
            )
            rec.writeoff_analytic_tag_all = allocation_lines.mapped("analytic_tag_ids")

    def _prepare_deduct_move_line(self, deduct):
        vals = super()._prepare_deduct_move_line(deduct)
        vals.update(
            {"fund_id": deduct.writeoff_fund_id and deduct.writeoff_fund_id.id or False}
        )
        return vals

    def _create_payment_vals_from_wizard(self):
        payment_vals = super()._create_payment_vals_from_wizard()
        if (
            not self.currency_id.is_zero(self.payment_difference)
            and self.payment_difference_handling == "reconcile"
        ):
            payment_vals["write_off_line_vals"]["fund_id"] = self.writeoff_fund_id.id
        return payment_vals

    def _update_vals_deduction(self, moves):
        res = super()._update_vals_deduction(moves)
        move_lines = moves.mapped("line_ids")
        self.writeoff_fund_all = move_lines.mapped("fund_all")
        self.writeoff_analytic_tag_all = move_lines.mapped("analytic_tag_all")
        self._onchange_budget_all()
        return res
