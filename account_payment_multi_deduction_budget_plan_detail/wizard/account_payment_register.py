# Copyright 2023 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import Command, api, fields, models


class AccountPaymentRegister(models.TransientModel):
    _name = "account.payment.register"
    _inherit = ["analytic.dimension.line", "account.payment.register"]
    _analytic_tag_field_name = "writeoff_analytic_tag_ids"

    writeoff_fund_id = fields.Many2one(
        comodel_name="budget.source.fund",
        string="Fund",
    )
    writeoff_fund_all = fields.Many2many(
        comodel_name="budget.source.fund",
    )
    writeoff_analytic_tag_ids = fields.Many2many(
        comodel_name="account.analytic.tag",
        relation="account_payment_register_tag_rel",
        column1="register_id",
        column2="tag_id",
        string="Analytic Tag",
    )
    writeoff_analytic_tag_all = fields.Many2many(
        comodel_name="account.analytic.tag",
        relation="account_payment_register_tag_all_rel",
        column1="register_id",
        column2="tag_all_id",
    )

    @api.onchange("analytic_distribution")
    def _onchange_budget_all(self):
        Analytic = self.env["account.analytic.account"]
        for rec in self:
            if not rec.analytic_distribution:
                continue

            account_analytic_ids = [
                int(v) for k in rec.analytic_distribution.keys() for v in k.split(",")
            ]
            analytics = Analytic.browse(account_analytic_ids)
            plan_lines = analytics.mapped("plan_line_detail_ids")
            rec.writeoff_fund_all = plan_lines.mapped("fund_id")
            rec.writeoff_fund_id = (
                rec.writeoff_fund_all._origin.id
                if len(rec.writeoff_fund_all) == 1
                else False
            )
            rec.writeoff_analytic_tag_all = plan_lines.mapped("analytic_tag_ids")

    def _prepare_deduct_move_line(self, deduct):
        vals = super()._prepare_deduct_move_line(deduct)
        vals.update(
            {
                "fund_id": deduct.writeoff_fund_id
                and deduct.writeoff_fund_id.id
                or False,
                "analytic_tag_ids": [Command.set(deduct.writeoff_analytic_tag_ids.ids)],
            }
        )
        return vals

    def _create_payment_vals_from_wizard(self, batch_result):
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        # payment difference
        if self.payment_difference_handling == "reconcile" and payment_vals.get(
            "write_off_line_vals", []
        ):
            payment_vals["write_off_line_vals"][0].update(
                {
                    "fund_id": self.writeoff_fund_id.id,
                    "analytic_tag_ids": [
                        Command.set(self.writeoff_analytic_tag_ids.ids)
                    ],
                }
            )
        return payment_vals

    def _update_vals_deduction(self, move_lines):
        """For case `Mark as fully paid`, Default analytic_tags and fund"""
        res = super()._update_vals_deduction(move_lines)

        self.writeoff_fund_all = move_lines.mapped("fund_all")
        self.writeoff_analytic_tag_all = move_lines.mapped("analytic_tag_all")
        return res
