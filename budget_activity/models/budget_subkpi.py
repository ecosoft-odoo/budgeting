# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BudgetKPITemplate(models.Model):
    _inherit = "budget.kpi"

    activity_ids = fields.One2many(
        comodel_name="budget.activity",
        inverse_name="kpi_id",
        readonly=True,
    )
