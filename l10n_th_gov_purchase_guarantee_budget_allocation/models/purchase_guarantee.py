# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, fields, models


class PurchaseGuarantee(models.Model):
    _name = "purchase.guarantee"
    _inherit = ["analytic.dimension.line", "purchase.guarantee"]
    _analytic_tag_field_name = "analytic_tag_ids"

    analytic_tag_all = fields.Many2many(
        comodel_name="account.analytic.tag",
        compute="_compute_analytic_tag_all",
    )
    fund_id = fields.Many2one(
        comodel_name="budget.source.fund",
    )
    fund_all = fields.Many2many(
        comodel_name="budget.source.fund",
        compute="_compute_fund_all",
    )

    @api.depends("analytic_account_id")
    def _compute_fund_all(self):
        for rec in self:
            origin_fund = False
            if rec.reference_model == "purchase.requisition":
                origin_fund = rec.reference.line_ids.mapped("fund_id")
            else:
                origin_fund = (
                    rec.reference_model
                    and rec.reference.order_line.mapped("fund_id")
                    or False
                )
            rec.fund_all = origin_fund

    @api.depends("analytic_account_id")
    def _compute_analytic_tag_all(self):
        for rec in self:
            analytic_tag_ids = rec.analytic_account_id.allocation_line_ids.mapped(
                "analytic_tag_ids"
            )
            rec.analytic_tag_all = analytic_tag_ids

    def _get_dimension_fields(self):
        if self.env.context.get("update_custom_fields"):
            return []  # Avoid to report these columns when not yet created
        return [x for x in self.fields_get().keys() if x.startswith("x_dimension_")]

    @api.onchange("analytic_tag_all")
    def _onchange_analytic_tag_all(self):
        """Default analytic tag, if equal dimension"""
        dimension_fields = self._get_dimension_fields()
        analytic_tag_all = self.analytic_tag_all._origin
        if not analytic_tag_all or (
            len(analytic_tag_all) != len(dimension_fields)
            and self[self._analytic_tag_field_name]
        ):
            return
        self[self._analytic_tag_field_name] = (
            analytic_tag_all
            if len(analytic_tag_all) == len(dimension_fields)
            else False
        )

    @api.onchange("fund_all")
    def _onchange_fund_all(self):
        for rec in self:
            rec.fund_id = rec.fund_all._origin.id if len(rec.fund_all) == 1 else False
