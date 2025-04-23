# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from markupsafe import Markup

from odoo import api, fields, models
from odoo.exceptions import UserError


class BudgetTransferItem(models.Model):
    _inherit = "budget.transfer.item"
    _analytic_tag_from_field_name = "analytic_tag_from_ids"
    _analytic_tag_to_field_name = "analytic_tag_to_ids"

    detail_line_from_ids = fields.Many2many(
        comodel_name="budget.plan.line.detail",
        relation="detail_line_transfer_from_rel",
        column1="transfer_line_from_id",
        column2="detail_line_from_id",
        compute="_compute_detail_line_from",
    )
    detail_line_to_ids = fields.Many2many(
        comodel_name="budget.plan.line.detail",
        relation="detail_line_transfer_to_rel",
        column1="transfer_line_to_id",
        column2="detail_line_to_id",
        compute="_compute_detail_line_to",
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
    def _compute_fund_from_all(self):
        for rec in self:
            allowed_funds = rec.budget_control_from_id.fund_ids
            rec.fund_from_all = allowed_funds

            current_fund = rec.fund_from_id
            if len(allowed_funds) == 1:
                rec.fund_from_id = allowed_funds.id
            elif not current_fund or current_fund not in allowed_funds:
                rec.fund_from_id = False

    @api.depends("budget_control_from_id")
    def _compute_analytic_tag_from_all(self):
        for rec in self:
            analytic_tag_ids = rec.budget_control_from_id.analytic_tag_ids
            rec.analytic_tag_from_all = analytic_tag_ids

    @api.depends(
        lambda self: (self._analytic_tag_from_field_name,)
        if self._analytic_tag_from_field_name
        else ()
    )
    def _compute_domain_tag_from(self):
        analytic_tag_field_name = self._analytic_tag_from_field_name
        for rec in self:
            domain_result = rec._dynamic_domain_transfer_analytic_tags(
                analytic_tag_field_name
            )
            domain = domain_result.get("domain", {}).get(analytic_tag_field_name, [])
            rec.domain_tag_from_ids = domain[0][2] if domain else []

    @api.depends("fund_from_id", "analytic_tag_from_ids")
    def _compute_detail_line_from(self):
        for rec in self:
            all_detail_lines = rec.budget_control_from_id.sudo().plan_line_detail_ids
            plan_detail_line = rec._filter_detail_line(
                all_detail_lines, rec.fund_from_id, rec.analytic_tag_from_ids
            )

            # For dimension not selected all, we need filter analytic tag for make sure
            # the analytic tag is same with selected tags
            rec.detail_line_from_ids = plan_detail_line.filtered(
                lambda line: line.analytic_tag_ids == self.analytic_tag_from_ids._origin
            )

    @api.depends("budget_control_to_id")
    def _compute_fund_to_all(self):
        for rec in self:
            allowed_funds = rec.budget_control_to_id.fund_ids
            rec.fund_to_all = allowed_funds

            current_fund = rec.fund_to_id
            if len(allowed_funds) == 1:
                rec.fund_to_id = allowed_funds.id
            elif not current_fund or current_fund not in allowed_funds:
                rec.fund_to_id = False

    @api.depends("budget_control_to_id")
    def _compute_analytic_tag_to_all(self):
        for rec in self:
            analytic_tag_ids = rec.budget_control_to_id.analytic_tag_ids
            rec.analytic_tag_to_all = analytic_tag_ids

    @api.depends(
        lambda self: (self._analytic_tag_to_field_name,)
        if self._analytic_tag_to_field_name
        else ()
    )
    def _compute_domain_tag_to(self):
        analytic_tag_field_name = self._analytic_tag_to_field_name
        for rec in self:
            domain_result = rec._dynamic_domain_transfer_analytic_tags(
                analytic_tag_field_name
            )
            domain = domain_result.get("domain", {}).get(analytic_tag_field_name, [])
            rec.domain_tag_to_ids = domain[0][2] if domain else []

    @api.depends("fund_to_id", "analytic_tag_to_ids")
    def _compute_detail_line_to(self):
        for rec in self:
            all_detail_lines = rec.budget_control_to_id.sudo().plan_line_detail_ids
            plan_detail_line = rec._filter_detail_line(
                all_detail_lines, rec.fund_to_id, rec.analytic_tag_to_ids
            )

            # For dimension not selected all, we need filter analytic tag for make sure
            # the analytic tag is same with selected tags
            rec.detail_line_to_ids = plan_detail_line.filtered(
                lambda line: line.analytic_tag_ids == self.analytic_tag_to_ids._origin
            )

    def _dynamic_domain_transfer_analytic_tags(self, analytic_tag_field_name):
        """
        - For dimension without by_sequence, always show
        - For dimension with by_sequence, only show tags by sequence
        - Option to filter next dimension based on selected_tags
        """
        Dimension = self.env["account.analytic.dimension"]
        Tag = self.env["account.analytic.tag"]

        # If no dimension uses sequence, show everything (no filter)
        if not Dimension.search_count([("by_sequence", "=", True)]):
            return {"domain": {analytic_tag_field_name: []}}

        # Tags from non-sequenced dimensions (always shown)
        base_tags = Tag.search(
            [
                "|",
                ("analytic_dimension_id", "=", False),
                ("analytic_dimension_id.by_sequence", "=", False),
            ]
        )

        # Find next dimension by_sequence
        selected_tags = self[analytic_tag_field_name]
        selected_dimensions = selected_tags.mapped("analytic_dimension_id").filtered(
            "by_sequence"
        )
        current_max_seq = max(selected_dimensions.mapped("sequence"), default=-1)

        next_dimension = Dimension.search(
            [("by_sequence", "=", True), ("sequence", ">", current_max_seq)],
            order="sequence",
            limit=1,
        )
        next_tag_ids = []
        if next_dimension and next_dimension.filtered_field_ids:
            # Filetered by previously selected_tags
            next_tag_list = []
            for field in next_dimension.filtered_field_ids:
                matched_tags = selected_tags.filtered(
                    lambda tag, field=field: tag.resource_ref
                    and tag.resource_ref._name == field.relation
                )
                matched_ids = [ref.id for ref in matched_tags.mapped("resource_ref")]
                dimension_tag_ids = next_dimension.analytic_tag_ids.filtered(
                    lambda tag, field=field, matched_ids=matched_ids: tag.resource_ref
                    and tag.resource_ref[field.name].id in matched_ids
                ).ids
                next_tag_list.append(set(dimension_tag_ids))
            # "&" to all in next_tag_list
            if next_tag_list:
                next_tag_ids = list(set.intersection(*next_tag_list))
        else:
            next_tag_ids = next_dimension.analytic_tag_ids.ids

        # Tags from non by_sequence dimension and next dimension
        all_tag_ids = base_tags.ids + next_tag_ids
        domain = [("id", "in", all_tag_ids)]
        return {"domain": {analytic_tag_field_name: domain}}

    def _filter_detail_line(self, all_detail_lines, fund, analytic_tags):
        domain = [("fund_id", "=", fund.id)]
        # For case dimension
        for tag in analytic_tags:
            field_dimension = tag.analytic_dimension_id.get_field_name(
                tag.analytic_dimension_id.code
            )
            domain.append((field_dimension, "=", tag._origin.id))
        return all_detail_lines.filtered_domain(domain)

    @api.depends(
        "detail_line_from_ids",
        "detail_line_to_ids",
        "fund_from_id",
        "analytic_tag_from_ids",
        "fund_to_id",
        "analytic_tag_to_ids",
    )
    def _compute_amount_available(self):
        res = super()._compute_amount_available()
        for rec in self:
            # Not update amount when transferred or reversed
            if rec.state in ["transfer", "reverse"]:
                continue

            # check condition for not error with query data
            if rec.fund_from_id or rec.analytic_tag_from_ids:
                detail_line_available = rec._get_detail_line_available(
                    rec.budget_control_from_id, rec.detail_line_from_ids
                )
                rec.amount_from_available = detail_line_available
            if rec.fund_to_id or rec.analytic_tag_to_ids:
                detail_line_available = rec._get_detail_line_available(
                    rec.budget_control_to_id, rec.detail_line_to_ids._origin
                )
                rec.amount_to_available = detail_line_available
        return res

    def _get_detail_line_available(self, budget_control, detail_lines):
        """Find amount available from detail released - consumed"""
        # Not found detail line return 0
        if not detail_lines:
            return 0

        # Released amount from plan line detail
        detail_line_released = sum(detail_lines.mapped("released_amount"))

        # Query fund consumed
        query_data = budget_control.budget_period_id._get_budget_avaiable(
            budget_control.analytic_account_id.id, detail_lines
        )
        # Result consumed is negative (-)
        consumed_fund_amount = sum(
            q["amount"] for q in query_data if q["amount"] is not None
        )
        return detail_line_released + consumed_fund_amount

    def _check_constraint_transfer(self):
        res = super()._check_constraint_transfer()
        if not (self.detail_line_from_ids and self.detail_line_to_ids):
            raise UserError(self.env._("Not found related budget detail lines!"))
        return res

    def _get_structured_message_transfer(self, budget_control, fund, analytic_tags):
        analytic_tag_name = ", ".join(analytic_tags.mapped("name")) or ""
        return {
            "budget": budget_control.name,
            "fund": fund.name,
            "tags": analytic_tag_name,
        }

    def _get_prepare_message_transfer(
        self, msg_from_data, msg_to_data, amount_str, symbol
    ):
        """Prepare message for budget transfer"""
        message = self.env._(
            f"""
                <strong>Budget Transfer Details</strong>
                <hr/>
                <strong>From:</strong>
                <dl style='margin-left: 15px;'>
                    <dt>Budget:</dt><dd>{msg_from_data.get("budget")}</dd>
                    <dt>Fund:</dt><dd>{msg_from_data.get("fund")}</dd>
                    <dt>Tags:</dt><dd>{msg_from_data.get("tags")}</dd>
                </dl>
                <strong>To:</strong>
                <dl style='margin-left: 15px;'>
                    <dt>Budget:</dt><dd>{msg_to_data.get("budget")}</dd>
                    <dt>Fund:</dt><dd>{msg_to_data.get("fund")}</dd>
                    <dt>Tags:</dt><dd>{msg_to_data.get("tags")}</dd>
                </dl>
                <hr/>
                <strong>Amount:</strong> %(amount)s %(symbol)s
            """
        )
        return message

    def transfer(self):
        res = super().transfer()
        symbol = self.env.company.currency_id.symbol
        self = self.sudo().with_context(allow_edit_plan_detail=1)
        for rec in self:
            transfer_amount = rec.amount
            # Transfer amount more than budget plan detail
            for detail_line in rec.detail_line_from_ids:
                if detail_line.released_amount < transfer_amount:
                    transfer_amount -= detail_line.released_amount
                    detail_line.released_amount = 0.0
                else:
                    detail_line.released_amount -= transfer_amount
            rec.detail_line_to_ids[0].released_amount += rec.amount

            # Log message to budget plan
            msg_from_data = rec._get_structured_message_transfer(
                self.budget_control_from_id, rec.fund_from_id, rec.analytic_tag_from_ids
            )
            msg_to_data = rec._get_structured_message_transfer(
                self.budget_control_to_id, rec.fund_to_id, rec.analytic_tag_to_ids
            )
            amount_str = f"{transfer_amount:,.2f}"
            mesesage_log = rec._get_prepare_message_transfer(
                msg_from_data, msg_to_data, amount_str, symbol
            )

            budget_plan = (rec.detail_line_from_ids + rec.detail_line_to_ids).mapped(
                "plan_id"
            )
            budget_plan.message_post(body=Markup(mesesage_log))
        return res

    def reverse(self):
        res = super().reverse()
        symbol = self.env.company.currency_id.symbol
        self = self.sudo().with_context(allow_edit_plan_detail=1)
        for rec in self:
            reverse_amount = rec.amount
            # Update release amount
            rec.detail_line_from_ids[0].released_amount += reverse_amount
            rec.detail_line_to_ids[0].released_amount -= reverse_amount

            # Log message to budget plan
            msg_from_data = rec._get_structured_message_transfer(
                self.budget_control_from_id, rec.fund_from_id, rec.analytic_tag_from_ids
            )
            msg_to_data = rec._get_structured_message_transfer(
                self.budget_control_to_id, rec.fund_to_id, rec.analytic_tag_to_ids
            )
            amount_str = f"{reverse_amount:,.2f}"
            mesesage_log = rec._get_prepare_message_transfer(
                msg_to_data, msg_from_data, amount_str, symbol
            )  # swap from and to

            budget_plan = (rec.detail_line_from_ids + rec.detail_line_to_ids).mapped(
                "plan_id"
            )
            budget_plan.message_post(body=Markup(mesesage_log))
        return res
