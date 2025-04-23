# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import UserError


class BudgetPlan(models.Model):
    _inherit = "budget.plan"

    line_detail_ids = fields.One2many(
        comodel_name="budget.plan.line.detail",
        inverse_name="plan_id",
        copy=True,
        context={"active_test": False},
    )
    is_confirm_plan = fields.Boolean(
        string="Confirm plan details",
        copy=False,
        tracking=True,
    )

    @api.depends("line_ids", "line_detail_ids")
    def _compute_total_amount(self):
        """Overwrite to show amount from details or plan"""
        for rec in self:
            if not rec.is_confirm_plan:
                rec.total_amount = sum(rec.line_detail_ids.mapped("allocated_amount"))
            else:
                rec.total_amount = sum(rec.line_ids.mapped("amount"))

    def _update_plan_line_relation(self):
        """Add relation between `plan line` and `plan line detail`"""
        plan_line_map = {line.analytic_account_id.id: line.id for line in self.line_ids}
        cr = self.env.cr
        line_detail_list = self.line_detail_ids.read(["id", "analytic_account_id"])
        for line_detail in line_detail_list:
            plan_line_id = plan_line_map.get(line_detail["analytic_account_id"][0])
            if plan_line_id:
                # Use SQL to update the plan_line_id in bulk
                # This is more efficient than using ORM for large datasets
                cr.execute(
                    """
                    UPDATE budget_plan_line_detail
                    SET plan_line_id = %s, released_amount = allocated_amount
                    WHERE id = %s
                    """,
                    (plan_line_id, line_detail["id"]),
                )
        self.env["budget.plan.line.detail"]._invalidate_cache()

    def action_confirm_plan_detail(self):
        # Update Plan Lines
        self.action_update_plan()

        # Update the plan line relation
        self._update_plan_line_relation()

        # Update the plan line amount with the sum of the allocated amounts
        grouped = defaultdict(float)
        for detail in self.line_detail_ids:
            if detail.plan_line_id:
                grouped[detail.plan_line_id.id] += detail.allocated_amount

        if grouped:
            lines_to_write = self.env["budget.plan.line"].browse(grouped.keys())
            for line in lines_to_write:
                line.amount = grouped.get(line.id, 0.0)
        return self.write({"is_confirm_plan": True})

    def action_cancel_plan_detail(self):
        return self.write({"is_confirm_plan": False})

    def button_open_budget_plan_detail(self):
        self.ensure_one()
        ctx = self.env.context.copy()
        ctx.update(
            {
                "create": False,
                "edit": False,
            }
        )
        return {
            "name": self.env._("Budget Plan Details"),
            "view_mode": "list",
            "res_model": "budget.plan.line.detail",
            "type": "ir.actions.act_window",
            "context": ctx,
            "domain": [
                ("plan_id", "=", self.id),
                (
                    "analytic_account_id",
                    "in",
                    self.line_ids.mapped("analytic_account_id").ids,
                ),
            ],
        }


class BudgetPlanLine(models.Model):
    _inherit = "budget.plan.line"

    plan_line_detail_ids = fields.One2many(
        comodel_name="budget.plan.line.detail",
        inverse_name="plan_line_id",
    )

    def open_plan_line_detail(self):
        self.ensure_one()
        ctx = self.env.context.copy()
        ctx.update(
            {
                "create": False,
                "edit": False,
            }
        )
        return {
            "name": self.env._("Budget Plan Details"),
            "view_mode": "list",
            "res_model": "budget.plan.line.detail",
            "type": "ir.actions.act_window",
            "context": ctx,
            "domain": [
                ("plan_id", "=", self.plan_id.id),
                ("analytic_account_id", "=", self.analytic_account_id.id),
            ],
        }


class BudgetPlanLineDetail(models.Model):
    _name = "budget.plan.line.detail"
    _inherit = "analytic.dimension.line"
    _description = "Plan Line Details"
    _rec_name = "id"  # For unique ref
    _check_company_auto = True
    _analytic_tag_field_name = "analytic_tag_ids"

    plan_id = fields.Many2one(
        comodel_name="budget.plan",
        required=True,
        index=True,
        ondelete="cascade",
    )
    plan_line_id = fields.Many2one(
        comodel_name="budget.plan.line",
        index=True,
    )
    budget_period_id = fields.Many2one(
        comodel_name="budget.period",
        related="plan_id.budget_period_id",
        store=True,
    )
    date_from = fields.Date(
        related="budget_period_id.bm_date_from",
        store=True,
    )
    date_to = fields.Date(
        related="budget_period_id.bm_date_to",
        store=True,
    )
    budget_control_id = fields.Many2one(
        comodel_name="budget.control",
        readonly=True,
    )
    name = fields.Char(string="Description")
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        required=True,
        index=True,
    )
    analytic_tag_ids = fields.Many2many(
        comodel_name="account.analytic.tag",
        string="Analytic Tags",
    )
    fund_id = fields.Many2one(
        comodel_name="budget.source.fund",
        required=True,
        index=True,
        ondelete="restrict",
    )
    fund_group_id = fields.Many2one(
        comodel_name="budget.source.fund.group",
        related="fund_id.fund_group_id",
        store=True,
    )
    estimated_amount = fields.Monetary(
        compute="_compute_estimated_amount",
        store=True,
        readonly=False,
        help="Estimated amount to be received this year",
    )
    allocated_amount = fields.Monetary(
        string="Allocated",
        help="Initial allocated amount",
    )
    released_amount = fields.Monetary(
        string="Released",
        help="Total current amount",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.user.company_id,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency", related="company_id.currency_id"
    )
    active = fields.Boolean(related="plan_id.active")

    @api.depends("allocated_amount")
    def _compute_estimated_amount(self):
        for rec in self:
            rec.estimated_amount = rec.estimated_amount or rec.allocated_amount

    @api.model_create_multi
    def create(self, vals):
        for val in vals:
            if val.get("plan_id"):
                plan = self.env["budget.plan"].browse(val.get("plan_id"))
                if plan.is_confirm_plan:
                    raise UserError(
                        self.env._(
                            "You cannot create a detail line for a confirmed plan. "
                            f"Please check plan {plan.name}."
                        )
                    )
        return super().create(vals)

    def write(self, vals):
        # NOTE: skip budget_control_id because function '_compute_line_detail_ids'
        # will compute and add budget_control_id in detail line
        # If not skip, it will not allow to edit detail line.
        if self.env.context.get("allow_edit_plan_detail") or vals.get(
            "budget_control_id"
        ):
            return super().write(vals)

        for rec in self:
            if rec.plan_id.is_confirm_plan:
                raise UserError(
                    self.env._(
                        "You cannot edit a detail line for a confirmed plan. "
                        f"Please check plan {rec.plan_id.name}."
                    )
                )
        return super().write(vals)
