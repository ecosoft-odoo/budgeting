# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResProgramAllocation(models.Model):
    _inherit = "res.program.allocation"

    program_ids = fields.Many2many(
        comodel_name="res.program",
        compute="_compute_all_data",
        relation="program_allocation_program_rel",
        column1="allocation_id",
        column2="program_id",
        help="Used to povide list of Program in excel sheet",
    )
    analytic_ids = fields.Many2many(
        comodel_name="account.analytic.account",
        compute="_compute_all_data",
        relation="program_allocation_analytic_rel",
        column1="allocation_id",
        column2="analytic_id",
        help="Used to povide list of Analytic in excel sheet",
    )
    fund_ids = fields.Many2many(
        comodel_name="budget.source.fund",
        compute="_compute_all_data",
        relation="program_allocation_fund_rel",
        column1="allocation_id",
        column2="fund_id",
        help="Used to povide list of Fund in excel sheet",
    )

    def _compute_all_data(self):
        all_program = self.env["res.program"].search([])
        all_fund = self.env["budget.source.fund"].search([])
        Analytic = self.env["account.analytic.account"]
        for rec in self:
            all_analytic = Analytic.search(
                [("budget_period_id", "=", rec.budget_period_id.id)]
            )
            rec.program_ids = [(6, 0, all_program.ids)]
            rec.analytic_ids = [(6, 0, all_analytic.ids)]
            rec.fund_ids = [(6, 0, all_fund.ids)]
