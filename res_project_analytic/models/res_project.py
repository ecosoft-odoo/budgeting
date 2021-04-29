# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResProject(models.Model):
    _inherit = "res.project"

    analytic_account_ids = fields.One2many(
        comodel_name="account.analytic.account",
        inverse_name="project_id",
        string="Analytic Account",
        copy=False,
        domain="['|', ('company_id', '=', False), "
        "('company_id', '=', company_id)]",
        check_company=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        help="Analytic account to which this project is linked for "
        "financial management. Use an analytic account to record cost "
        "and revenue on your project.",
    )
