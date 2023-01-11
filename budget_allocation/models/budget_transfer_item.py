# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class BudgetTransferItem(models.Model):
    _inherit = "budget.transfer.item"
    _analytic_tag_from_field_name = "analytic_tag_from_ids"
    _analytic_tag_to_field_name = "analytic_tag_to_ids"

    allocation_line_from_ids = fields.Many2many(
        comodel_name="budget.allocation.line",
        relation="allocation_line_transfer_from_rel",
        column1="transfer_line_from_id",
        column2="allocation_line_from_id",
        compute="_compute_allocation_line_from",
    )
    allocation_line_to_ids = fields.Many2many(
        comodel_name="budget.allocation.line",
        relation="allocation_line_transfer_to_rel",
        column1="transfer_line_to_id",
        column2="allocation_line_to_id",
        compute="_compute_allocation_line_to",
    )
    fund_from_id = fields.Many2one(
        comodel_name="budget.source.fund",
        string="Fund From",
        ondelete="restrict",
        required=True,
    )
    fund_from_all = fields.Many2many(
        comodel_name="budget.source.fund",
        compute="_compute_fund_from_all",
    )
    analytic_tag_from_ids = fields.Many2many(
        comodel_name="account.analytic.tag",
        string="Analytic Tags From",
        relation="budget_control_analytic_tag_from_rel",
        column1="budget_control_from_id",
        column2="analytic_tag_from_id",
    )
    domain_tag_from_ids = fields.Many2many(
        comodel_name="account.analytic.tag",
        compute="_compute_domain_tag_from",
        help="Helper field, the filtered tags_ids when record is saved",
    )
    analytic_tag_from_all = fields.Many2many(
        comodel_name="account.analytic.tag",
        compute="_compute_analytic_tag_from_all",
    )
    fund_to_id = fields.Many2one(
        comodel_name="budget.source.fund",
        string="Fund To",
        ondelete="restrict",
        required=True,
    )
    fund_to_all = fields.Many2many(
        comodel_name="budget.source.fund",
        compute="_compute_fund_to_all",
    )
    analytic_tag_to_ids = fields.Many2many(
        comodel_name="account.analytic.tag",
        string="Analytic Tags To",
        relation="budget_control_analytic_tag_to_rel",
        column1="budget_control_to_id",
        column2="analytic_tag_to_id",
    )
    domain_tag_to_ids = fields.Many2many(
        comodel_name="account.analytic.tag",
        compute="_compute_domain_tag_to",
        help="Helper field, the filtered tags_ids when record is saved",
    )
    analytic_tag_to_all = fields.Many2many(
        comodel_name="account.analytic.tag",
        compute="_compute_analytic_tag_to_all",
    )

    @api.depends("budget_control_from_id")
    def _compute_analytic_tag_from_all(self):
        for rec in self:
            analytic_tag_ids = rec.budget_control_from_id.analytic_tag_ids
            analytic_tag_ids.mapped("analytic_dimension_id")
            rec.analytic_tag_from_all = analytic_tag_ids

    @api.depends("budget_control_to_id")
    def _compute_analytic_tag_to_all(self):
        for rec in self:
            analytic_tag_ids = rec.budget_control_to_id.analytic_tag_ids
            analytic_tag_ids.mapped("analytic_dimension_id")
            rec.analytic_tag_to_all = analytic_tag_ids

    @api.depends(
        lambda self: (self._analytic_tag_from_field_name,)
        if self._analytic_tag_from_field_name
        else ()
    )
    def _compute_domain_tag_from(self):
        analytic_tag_field_name = self._analytic_tag_from_field_name
        res = {}
        for rec in self:
            tag_ids = []
            res = rec._dynamic_domain_transfer_analytic_tags(analytic_tag_field_name)
            if res["domain"][analytic_tag_field_name]:
                tag_ids = res["domain"][analytic_tag_field_name][0][2]
            rec.domain_tag_from_ids = tag_ids

    @api.depends(
        lambda self: (self._analytic_tag_to_field_name,)
        if self._analytic_tag_to_field_name
        else ()
    )
    def _compute_domain_tag_to(self):
        analytic_tag_field_name = self._analytic_tag_to_field_name
        res = {}
        for rec in self:
            tag_ids = []
            res = rec._dynamic_domain_transfer_analytic_tags(analytic_tag_field_name)
            if res["domain"][analytic_tag_field_name]:
                tag_ids = res["domain"][analytic_tag_field_name][0][2]
            rec.domain_tag_to_ids = tag_ids

    @api.depends("budget_control_from_id")
    def _compute_fund_from_all(self):
        for rec in self:
            fund_ids = rec.budget_control_from_id.fund_ids
            rec.fund_from_all = fund_ids
            if len(fund_ids) > 1 and rec.fund_from_id and rec.fund_from_id in fund_ids:
                continue
            rec.fund_from_id = len(fund_ids) == 1 and fund_ids.id or False

    @api.depends("budget_control_to_id")
    def _compute_fund_to_all(self):
        for rec in self:
            fund_ids = rec.budget_control_to_id.fund_ids
            rec.fund_to_all = fund_ids
            if len(fund_ids) > 1 and rec.fund_to_id and rec.fund_to_id in fund_ids:
                continue
            rec.fund_to_id = len(fund_ids) == 1 and fund_ids.id or False

    @api.depends("fund_from_id", "analytic_tag_from_ids")
    def _compute_allocation_line_from(self):
        for rec in self:
            all_allocations = rec.budget_control_from_id.sudo().allocation_line_ids
            allocation_lines = all_allocations.filtered_domain(
                rec._get_domain_allocation_line_from()
            )
            rec.allocation_line_from_ids = allocation_lines.filtered(
                lambda l: l.analytic_tag_ids == self.analytic_tag_from_ids._origin
            )

    @api.depends("fund_to_id", "analytic_tag_to_ids")
    def _compute_allocation_line_to(self):
        for rec in self:
            all_allocations = rec.budget_control_to_id.sudo().allocation_line_ids
            allocation_lines = all_allocations.filtered_domain(
                rec._get_domain_allocation_line_to()
            )
            rec.allocation_line_to_ids = allocation_lines.filtered(
                lambda l: l.analytic_tag_ids == self.analytic_tag_to_ids._origin
            )

    @api.depends(
        "fund_from_id", "fund_to_id", "analytic_tag_from_ids", "analytic_tag_to_ids"
    )
    def _compute_amount_available(self):
        res = super()._compute_amount_available()
        for rec in self:
            # check condition for not error with query data
            if rec.fund_from_id or rec.analytic_tag_from_ids:
                allocation_line_from_available = rec._get_allocation_line_available(
                    rec.allocation_line_from_ids._origin
                )
                rec.amount_from_available = allocation_line_from_available
            if rec.fund_to_id or rec.analytic_tag_to_ids:
                allocation_line_to_available = rec._get_allocation_line_available(
                    rec.allocation_line_to_ids._origin
                )
                rec.amount_to_available = allocation_line_to_available
        return res

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
                    lambda l: l.resource_ref and l.resource_ref._name == field.relation
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

    def _get_allocation_line_available(self, allocation_lines):
        """Find amount available from allocation released - consumed"""
        # Not found allocation line return 0
        if not allocation_lines:
            return 0
        allocation_line_released = sum(allocation_lines.mapped("released_amount"))
        # Query fund consumed
        budget_control = self.budget_control_from_id
        query_data = budget_control.budget_period_id._get_budget_avaiable(
            budget_control.analytic_account_id.id, allocation_lines
        )
        consumed_fund_amount = sum(
            q["amount"] for q in query_data if q["amount"] is not None
        )
        return allocation_line_released - consumed_fund_amount

    def _get_domain_allocation_line_from(self):
        domain = [("fund_id", "=", self.fund_from_id.id)]
        for tag in self.analytic_tag_from_ids:
            field_dimension = tag.analytic_dimension_id.get_field_name(
                tag.analytic_dimension_id.code
            )
            domain.append((field_dimension, "=", tag._origin.id))
        return domain

    def _get_domain_allocation_line_to(self):
        domain = [("fund_id", "=", self.fund_to_id.id)]
        for tag in self.analytic_tag_to_ids:
            field_dimension = tag.analytic_dimension_id.get_field_name(
                tag.analytic_dimension_id.code
            )
            domain.append((field_dimension, "=", tag._origin.id))
        return domain

    def _check_constraint_transfer(self):
        res = super()._check_constraint_transfer()
        if not (self.allocation_line_from_ids and self.allocation_line_to_ids):
            raise UserError(_("Not found related budget allocation lines!"))
        return res

    def _get_message_transfer_from(self):
        analytic_tag_name = ", ".join(self.analytic_tag_from_ids.mapped("name"))
        return "From Budget: {}<br/>Fund: {}<br/>Analytic Tags: {}".format(
            self.budget_control_from_id.name, self.fund_from_id.name, analytic_tag_name
        )

    def _get_message_transfer_to(self):
        analytic_tag_name = ", ".join(self.analytic_tag_to_ids.mapped("name"))
        return "To Budget: {}<br/>Fund: {}<br/>Analytic Tags: {}".format(
            self.budget_control_to_id.name, self.fund_to_id.name, analytic_tag_name
        )

    def transfer(self):
        res = super().transfer()
        for rec in self:
            transfer_amount = rec.amount
            # Transfer amount more than budget allocation per line
            for ba_line in rec.allocation_line_from_ids:
                if ba_line.released_amount < transfer_amount:
                    transfer_amount -= ba_line.released_amount
                    ba_line.released_amount = 0.0
                else:
                    ba_line.released_amount -= transfer_amount
            rec.allocation_line_to_ids[0].released_amount += rec.amount
            # Log message to budget allocation
            allocation_lines = rec.allocation_line_from_ids + rec.allocation_line_to_ids
            budget_allocation_ids = allocation_lines.mapped("budget_allocation_id")
            message = _(
                "{}<br/><b>transfer to</b><br/>{}<br/>with amount {:,.2f} {}"
            ).format(
                rec._get_message_transfer_from(),
                rec._get_message_transfer_to(),
                rec.amount,
                self.env.company.currency_id.symbol,
            )
            budget_allocation_ids.message_post(body=message)
        return res

    def reverse(self):
        res = super().reverse()
        for rec in self:
            reverse_amount = rec.amount
            # Update release amount
            rec.allocation_line_from_ids[0].released_amount += reverse_amount
            rec.allocation_line_to_ids[0].released_amount -= reverse_amount
            # Log message to budget allocation
            allocation_lines = rec.allocation_line_from_ids + rec.allocation_line_to_ids
            budget_allocation_ids = allocation_lines.mapped("budget_allocation_id")
            message = _(
                "{}<br/><b>reverse from</b><br/>{}<br/>with amount {:,.2f} {}"
            ).format(
                rec._get_message_transfer_from(),
                rec._get_message_transfer_to(),
                rec.amount,
                self.env.company.currency_id.symbol,
            )
            budget_allocation_ids.message_post(body=message)
        return res
