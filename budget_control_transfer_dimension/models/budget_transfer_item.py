# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class BudgetTransferItem(models.Model):
    _inherit = "budget.transfer.item"
    _analytic_tag_source_field_name = "source_analytic_tag_ids"
    _analytic_tag_target_field_name = "target_analytic_tag_ids"

    source_analytic_tag_ids = fields.Many2many(
        comodel_name="account.analytic.tag",
        string="Source Analytic Tags",
        relation="source_budget_control_analytic_tag_rel",
        column1="source_budget_control_id",
        column2="source_analytic_tag_id",
    )
    source_domain_tag_ids = fields.Many2many(
        comodel_name="account.analytic.tag",
        compute="_compute_source_analytic_tags_domain",
        help="Helper field, the filtered tags_ids when record is saved",
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
    target_domain_tag_ids = fields.Many2many(
        comodel_name="account.analytic.tag",
        compute="_compute_target_analytic_tags_domain",
        help="Helper field, the filtered tags_ids when record is saved",
    )

    @api.depends(
        lambda self: (self._analytic_tag_source_field_name,)
        if self._analytic_tag_source_field_name
        else ()
    )
    def _compute_source_analytic_tags_domain(self):
        analytic_tag_field_name = self._analytic_tag_source_field_name
        res = {}
        for rec in self:
            tag_ids = []
            res = rec._dynamic_domain_transfer_analytic_tags(
                analytic_tag_field_name
            )
            if res["domain"][analytic_tag_field_name]:
                tag_ids = res["domain"][analytic_tag_field_name][0][2]
            rec.source_domain_tag_ids = tag_ids

    @api.depends(
        lambda self: (self._analytic_tag_target_field_name,)
        if self._analytic_tag_target_field_name
        else ()
    )
    def _compute_target_analytic_tags_domain(self):
        analytic_tag_field_name = self._analytic_tag_target_field_name
        res = {}
        for rec in self:
            tag_ids = []
            res = rec._dynamic_domain_transfer_analytic_tags(
                analytic_tag_field_name
            )
            if res["domain"][analytic_tag_field_name]:
                tag_ids = res["domain"][analytic_tag_field_name][0][2]
            rec.target_domain_tag_ids = tag_ids

    def _dynamic_domain_transfer_analytic_tags(self, analytic_tag_field_name):
        """
        - For dimension without by_sequence, always show
        - For dimension with by_sequence, only show tags by sequence
        - Option to filter next dimension based on selected_tags
        """
        Dimension = self.env["account.analytic.dimension"]
        Tag = self.env["account.analytic.tag"]
        # If no dimension with by_sequence, nothing to filter, exist
        count = Dimension.search_count([("by_sequence", "=", True)])
        if count == 0:
            return {"domain": {analytic_tag_field_name: []}}
        # Find non by_sequence tags, to show always
        tags = Tag.search(
            [
                "|",
                ("analytic_dimension_id", "=", False),
                ("analytic_dimension_id.by_sequence", "=", False),
            ]
        )
        # Find next dimension by_sequence
        selected_tags = self[analytic_tag_field_name]
        sequences = (
            selected_tags.mapped("analytic_dimension_id")
            .filtered("by_sequence")
            .mapped("sequence")
        )
        cur_sequence = sequences and max(sequences) or -1
        next_dimension = Dimension.search(
            [("by_sequence", "=", True), ("sequence", ">", cur_sequence)],
            order="sequence",
            limit=1,
        )
        next_tag_ids = []
        if next_dimension and next_dimension.filtered_field_ids:
            # Filetered by previously selected_tags
            next_tag_list = []
            for field in next_dimension.filtered_field_ids:
                matched_tags = selected_tags.filtered(
                    lambda l: l.resource_ref
                    and l.resource_ref._name == field.relation
                )
                tag_resources = matched_tags.mapped("resource_ref")
                res_ids = tag_resources and [x.id for x in tag_resources] or []
                tag_ids = next_dimension.analytic_tag_ids.filtered(
                    lambda l: l.resource_ref[field.name].id in res_ids
                ).ids
                next_tag_list.append(set(tag_ids))
            # "&" to all in next_tag_list
            next_tag_ids = list(set.intersection(*map(set, next_tag_list)))
        else:
            next_tag_ids = next_dimension.analytic_tag_ids.ids
        # Tags from non by_sequence dimension and next dimension
        tag_ids = tags.ids + next_tag_ids
        # tag_ids = tags.ids + next_tag_ids
        domain = [("id", "in", tag_ids)]
        return {"domain": {analytic_tag_field_name: domain}}

    @api.depends("source_budget_control_id")
    def _compute_source_analytic_tag_all(self):
        for doc in self:
            analytic_tag_ids = doc.source_budget_control_id.analytic_tag_ids
            dimension_fields = analytic_tag_ids.mapped("analytic_dimension_id")
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
            doc.source_analytic_tag_ids = (
                len(analytic_tag_ids) == len(dimension_fields)
                and analytic_tag_ids
                or False
            )

    @api.depends("target_budget_control_id")
    def _compute_target_analytic_tag_all(self):
        for doc in self:
            analytic_tag_ids = doc.target_budget_control_id.analytic_tag_ids
            dimension_fields = analytic_tag_ids.mapped("analytic_dimension_id")
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
            doc.target_analytic_tag_ids = (
                len(analytic_tag_ids) == len(dimension_fields)
                and analytic_tag_ids
                or False
            )

    def _filter_context_amount_available(self):
        ctx = super()._filter_context_amount_available()
        ctx["filter_analytic_tag_ids"] = self.source_analytic_tag_ids.ids
        return ctx

    def _get_domain_source_allocation_line(self):
        res = super()._get_domain_source_allocation_line()
        source_analytic_tag = self.source_analytic_tag_ids
        dimensions = source_analytic_tag.mapped("analytic_dimension_id")
        tags_list = [
            (
                dimension.get_field_name(dimension.code),
                "=",
                source_analytic_tag.filtered(
                    lambda l: l.analytic_dimension_id == dimension
                ).id,
            )
            for dimension in dimensions
        ]
        return res + tags_list

    def _get_domain_target_allocation_line(self):
        res = super()._get_domain_target_allocation_line()
        target_analytic_tag = self.target_analytic_tag_ids
        dimensions = target_analytic_tag.mapped("analytic_dimension_id")
        tags_list = [
            (
                dimension.get_field_name(dimension.code),
                "=",
                target_analytic_tag.filtered(
                    lambda l: l.analytic_dimension_id == dimension
                ).id,
            )
            for dimension in dimensions
        ]
        return res + tags_list

    def _check_constraint_transfer(self):
        super()._check_constraint_transfer()
        source_lines, target_lines = self._get_budget_allocation_lines()
        # Filtered with dimension,
        # for case user not selected analytic tag on budget transfer.
        source_line = source_lines.mapped("analytic_tag_ids").filtered(
            lambda l: l.id in self.source_analytic_tag_ids.ids
        )
        target_line = target_lines.mapped("analytic_tag_ids").filtered(
            lambda l: l.id in self.target_analytic_tag_ids.ids
        )
        if not (source_line and target_line):
            raise UserError(
                _("Source / Target Analytic Tags is not selected.")
            )

    def _get_message_source_transfer(self):
        source_transfer = super()._get_message_source_transfer()
        analytic_tag_name = ", ".join(
            self.source_analytic_tag_ids.mapped("name")
        )
        return "<br/>Analytic Tags: ".join(
            [source_transfer, analytic_tag_name]
        )

    def _get_message_target_transfer(self):
        target_transfer = super()._get_message_target_transfer()
        analytic_tag_name = ", ".join(
            self.target_analytic_tag_ids.mapped("name")
        )
        return "<br/>Analytic Tags: ".join(
            [target_transfer, analytic_tag_name]
        )
