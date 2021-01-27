# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class BudgetControl(models.Model):
    _inherit = "budget.control"

    fund_ids = fields.Many2many(
        comodel_name="budget.source.fund",
        string="Funds",
        copy=False,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    fund_line_ids = fields.One2many(
        comodel_name="budget.source.fund.line",
        inverse_name="budget_control_id",
    )

    @api.constrains("item_ids", "fund_line_ids")
    def _check_fund_amount(self):
        for rec in self:
            plan_amount = sum(rec.item_ids.mapped("amount"))
            fund_amount = sum(rec.fund_line_ids.mapped("amount"))
            currency_id = rec.company_id.currency_id
            if (
                float_compare(
                    plan_amount,
                    fund_amount,
                    precision_rounding=currency_id.rounding,
                )
                == 1
            ):
                raise UserError(
                    _(
                        "you can plan total amount not more than %.2f%s"
                        % (fund_amount, currency_id.symbol)
                    )
                )

    def _get_fund_line_list(self, fund):
        fund_line_created = fund.fund_line_ids.filtered(
            lambda l: l.budget_control_id.id == self.id
        )
        if fund_line_created:
            val_list = (6, 0, fund_line_created.ids)
        else:
            val_list = (
                0,
                0,
                {
                    "fund_id": fund.id,
                    "date_from": self.date_from,
                    "date_to": self.date_to,
                    "budget_control_id": self.id,
                },
            )
        return val_list

    def write(self, vals):
        fund_obj = self.env["budget.source.fund"]
        fund_val_ids = vals.get("fund_ids", False)
        if fund_val_ids and fund_val_ids[0]:
            for rec in self:
                if not fund_val_ids[0][2]:
                    rec.fund_line_ids.unlink()
                    continue
                fund_ids = fund_obj.browse(fund_val_ids[0][2])
                fund_lines = [
                    rec._get_fund_line_list(fund) for fund in fund_ids
                ]
                vals.update({"fund_line_ids": fund_lines})
        res = super().write(vals)
        return res
