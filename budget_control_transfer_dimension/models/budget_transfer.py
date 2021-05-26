# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class BudgetTransferItem(models.Model):
    _inherit = "budget.transfer.item"

    source_analytic_tag_ids = fields.Many2many(
        comodel_name="account.analytic.tag",
        string="Source Analytic Tags",
        relation="source_budget_control_analytic_tag_rel",
        column1="source_budget_control_id",
        column2="source_analytic_tag_id",
    )
    source_analytic_tag_all = fields.Many2many(
        comodel_name="account.analytic.tag",
        compute="_compute_source_analytic_tag_all",
        compute_sudo=True,
    )
    target_analytic_tag_ids = fields.Many2many(
        comodel_name="account.analytic.tag",
        string="Target Analytic Tags",
        relation="target_budget_control_analytic_tag_rel",
        column1="target_budget_control_id",
        column2="target_analytic_tag_id",
    )
    target_analytic_tag_all = fields.Many2many(
        comodel_name="account.analytic.tag",
        compute="_compute_target_analytic_tag_all",
        compute_sudo=True,
    )

    def _get_dimension_fields(self):
        if self.env.context.get("update_custom_fields"):
            return []  # Avoid to report these columns when not yet created
        return [
            x for x in self.fields_get().keys() if x.startswith("x_dimension_")
        ]

    @api.depends("source_budget_control_id")
    def _compute_source_analytic_tag_all(self):
        for doc in self:
            dimension_fields = doc._get_dimension_fields()
            analytic_tag_ids = doc.source_budget_control_id.analytic_tag_ids
            doc.source_analytic_tag_all = analytic_tag_ids
            if (
                len(analytic_tag_ids) != len(dimension_fields)
                and doc.source_analytic_tag_ids
                and any(
                    x in analytic_tag_ids.ids
                    for x in doc.source_analytic_tag_ids.ids
                )
            ):
                continue
            doc.source_analytic_tag_ids = analytic_tag_ids

    @api.depends("target_budget_control_id")
    def _compute_target_analytic_tag_all(self):
        for doc in self:
            dimension_fields = doc._get_dimension_fields()
            analytic_tag_ids = doc.target_budget_control_id.analytic_tag_ids
            doc.target_analytic_tag_all = analytic_tag_ids
            if (
                len(analytic_tag_ids) != len(dimension_fields)
                and doc.target_analytic_tag_ids
                and any(
                    x in analytic_tag_ids.ids
                    for x in doc.target_analytic_tag_ids.ids
                )
            ):
                continue
            doc.target_analytic_tag_ids = analytic_tag_ids
