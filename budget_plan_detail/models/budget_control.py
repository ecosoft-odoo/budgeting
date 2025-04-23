# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class BudgetControl(models.Model):
    _inherit = "budget.control"

    plan_line_detail_ids = fields.One2many(
        comodel_name="budget.plan.line.detail",
        inverse_name="budget_control_id",
        compute="_compute_line_detail_ids",
        store=True,
    )
    fund_ids = fields.Many2many(
        comodel_name="budget.source.fund",
        relation="budget_control_source_fund_rel",
        column1="budget_control_id",
        column2="fund_id",
        compute="_compute_line_detail_ids",
        store=True,
        string="Funds",
        readonly=True,
    )
    # Change field to compute following allocation lines
    analytic_tag_ids = fields.Many2many(
        comodel_name="account.analytic.tag",
        string="Analytic Tags",
        compute="_compute_line_detail_ids",
        store=True,
    )

    @api.depends("analytic_account_id")
    def _compute_line_detail_ids(self):
        for rec in self:
            line_details = rec.analytic_account_id.plan_line_detail_ids.filtered(
                lambda line, rec=rec: line.budget_period_id == rec.budget_period_id
            )
            rec.plan_line_detail_ids = line_details
            rec.fund_ids = line_details.mapped("fund_id")
            rec.analytic_tag_ids = line_details.mapped("analytic_tag_ids")
