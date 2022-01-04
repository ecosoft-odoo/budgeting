# Copyright 2021 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models


class AccountPaymentDeduction(models.TransientModel):
    _inherit = "account.payment.deduction"

    analytic_tag_ids = fields.Many2many(
        comodel_name="account.analytic.tag",
        string="Analytic Tags",
        index=True,
        domain="[('id', 'in', analytic_tag_all)]",
    )
    analytic_tag_all = fields.Many2many(
        comodel_name="account.analytic.tag",
        compute="_compute_analytic_tag_all",
        compute_sudo=True,
    )

    @api.onchange("analytic_tag_all")
    def _onchange_analytic_tag_all(self):
        dimension_fields = self._get_dimension_fields()
        analytic_tag_ids = self.analytic_account_id.allocation_line_ids.mapped("analytic_tag_ids")
        if (
            len(analytic_tag_ids) != len(dimension_fields)
            and self.analytic_tag_ids
        ):
            return
        self.analytic_tag_ids = (
            len(analytic_tag_ids) == len(dimension_fields)
            and analytic_tag_ids
            or False
        )

    def _get_dimension_fields(self):
        return [
            x for x in self.fields_get().keys() if x.startswith("x_dimension_")
        ]

    @api.depends("analytic_account_id")
    def _compute_analytic_tag_all(self):
        for rec in self:
            analytic_tag_ids = rec.analytic_account_id.allocation_line_ids.mapped("analytic_tag_ids")
            rec.analytic_tag_all = analytic_tag_ids
