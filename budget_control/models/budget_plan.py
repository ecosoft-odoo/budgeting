# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import Command, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class BudgetPlan(models.Model):
    _name = "budget.plan"
    _description = "Budget Plan"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        required=True,
        tracking=True,
    )
    budget_period_id = fields.Many2one(
        comodel_name="budget.period",
        required=True,
    )
    date_from = fields.Date(related="budget_period_id.bm_date_from")
    date_to = fields.Date(related="budget_period_id.bm_date_to")
    budget_control_ids = fields.One2many(
        comodel_name="budget.control",
        compute="_compute_budget_control",
    )
    budget_control_count = fields.Integer(
        string="# of Budget Control",
        compute="_compute_budget_control",
        help="Count budget control in Plan",
    )
    total_amount = fields.Monetary(compute="_compute_total_amount")
    company_ids = fields.Many2many(
        comodel_name="res.company",
        relation="budget_plan_company_rel",
        column1="budget_plan_id",
        column2="company_id",
        string="Companies",
        default=lambda self: self.env.context.get("allowed_company_ids"),
        tracking=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency", compute="_compute_currency_id"
    )
    line_ids = fields.One2many(
        comodel_name="budget.plan.line",
        inverse_name="plan_id",
        copy=True,
        context={"active_test": False},
    )
    active = fields.Boolean(default=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirm", "Confirmed"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        default="draft",
        tracking=True,
    )

    @api.depends("company_ids")
    def _compute_currency_id(self):
        for rec in self:
            currencies = rec.company_ids.mapped(
                "currency_id"
            )  # Get all currencies from companies
            unique_currencies = set(currencies.ids)  # Get unique currency IDs
            if len(unique_currencies) > 1:
                raise UserError(
                    self.env._("Selected companies have different currencies!")
                )

            rec.currency_id = next(iter(currencies), self.env.company.currency_id)

    @api.depends("line_ids")
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped("amount"))

    @api.depends("line_ids")
    def _compute_budget_control(self):
        """Find all budget controls of the same period"""
        for rec in self.with_context(active_test=False).sudo():
            rec.budget_control_ids = rec.line_ids.mapped("budget_control_ids")
            rec.budget_control_count = len(rec.line_ids.mapped("budget_control_ids"))

    def button_open_budget_control(self):
        self.ensure_one()
        # Get budget controls in one query with proper context
        budget_controls = self.with_context(
            create=False,
            active_test=False,
            search_default_current_period=False,
        ).budget_control_ids

        action = {
            "name": self.env._("Budget Control Sheet"),
            "type": "ir.actions.act_window",
            "res_model": "budget.control",
            "view_mode": "list,form",
            "domain": [("id", "in", budget_controls.ids)],
        }
        return action

    def _prepare_budget_control_sheet(self, analytic_plan, **kwargs):
        self.ensure_one()
        plan_date_range_id = self.budget_period_id.plan_date_range_type_id.id
        currency_id = self.currency_id.id
        budget_period = self.budget_period_id
        # Additional params
        template_lines = kwargs.get("template_lines", [])
        use_all_kpis = kwargs.get("use_all_kpis", False)
        return [
            {
                "analytic_account_id": x.id,
                "name": f"{budget_period.name} :: {x.name}",
                "plan_date_range_type_id": plan_date_range_id,
                "use_all_kpis": use_all_kpis,
                "template_line_ids": template_lines,
                "budget_period_id": budget_period.id,
                "currency_id": currency_id,
            }
            for x in analytic_plan
        ]

    def _create_budget_controls(self, vals):
        return self.env["budget.control"].create(vals)

    def _update_budget_control_values(self):
        plan_line = self.line_ids.with_context(active_test=False)
        dp = self.currency_id.decimal_places
        for line in plan_line:
            budget_control = line.budget_control_ids.filtered("active")
            if not budget_control:
                budget_control = line.budget_control_ids.sorted("id")[-1:]
            if (
                float_compare(
                    budget_control.allocated_amount,
                    line.allocated_amount,
                    precision_digits=dp,
                )
                != 0
                or budget_control.active != line.active_status
            ):
                budget_control.action_draft()
                budget_control.write(
                    {
                        "allocated_amount": line.allocated_amount,
                        "active": line.active_status,
                    }
                )
        return True

    def action_create_update_budget_control(self):
        self.ensure_one()
        analytic_plan = self.line_ids.mapped("analytic_account_id")
        # Skip if budget control already exists
        existing_budget_controls = self.with_context(
            active_test=False
        ).budget_control_ids
        existing_analytics = existing_budget_controls.mapped("analytic_account_id")
        new_analytic = analytic_plan - existing_analytics

        # Create new budget control if new plan line is added
        if new_analytic:
            # Prepare budget control
            value_bc = self._prepare_budget_control_sheet(new_analytic)
            # Create budget controls that are not already exists
            new_budget_controls = self._create_budget_controls(value_bc)

            new_budget_controls.prepare_budget_control_matrix()

        # Update budget control values
        self._update_budget_control_values()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "message": self.env._("Budget Control has been updated!"),
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def check_plan_consumed(self):
        prec_digits = self.currency_id.decimal_places
        for line in self.mapped("line_ids"):
            amount = line.amount
            # Check amount + transferred is less than the amount consumed
            if (
                float_compare(
                    amount + line.budget_control_ids.transferred_amount,
                    line.amount_consumed,
                    precision_digits=prec_digits,
                )
                == -1
            ):
                raise UserError(
                    self.env._(
                        f"{line.analytic_account_id.display_name} "
                        f"has amount less than consumed."
                    )
                )
            # Update allocated/released if changed
            if line.allocated_amount != amount or line.released_amount != amount:
                # NOTE: If lines are large, this can change to direct SQL
                # to update the plan line
                line.write(
                    {
                        "allocated_amount": amount,
                        "released_amount": amount,
                    }
                )

    def action_update_amount_consumed(self):
        """Update amount consumed and released from budget control"""
        for rec in self:
            for line in rec.line_ids:
                # find consumed amount from budget control
                active_control = line.budget_control_ids
                if not active_control:
                    continue

                if len(active_control) > 1:
                    raise UserError(
                        self.env._(
                            f"{line.analytic_account_id.display_name} should have "
                            f"only 1 active budget control"
                        )
                    )
                line.amount_consumed = active_control.amount_consumed
                line.released_amount = active_control.released_amount

    def _prepare_update_plan_lines(self, analytics):
        lines = []
        for analytic in analytics:
            active_control = analytic.budget_control_ids.filtered(
                lambda control, self=self: control.budget_period_id
                == self.budget_period_id
            )
            lines.append(
                Command.create(
                    {
                        "analytic_account_id": analytic.id,
                        "amount_consumed": active_control.amount_consumed,
                        "released_amount": active_control.released_amount,
                    }
                )
            )
        return lines

    def action_update_plan(self):
        """Update plan line is not in plan line"""
        Analytic = self.env["account.analytic.account"]

        for rec in self:
            existing_analytic_ids = set(rec.line_ids.mapped("analytic_account_id.id"))
            domain = [
                ("bm_date_from", "<=", rec.date_to),
                ("bm_date_to", ">=", rec.date_from),
            ]
            if existing_analytic_ids:
                domain.append(("id", "not in", list(existing_analytic_ids)))

            new_analytics = Analytic.search(domain)

            lines = rec._prepare_update_plan_lines(new_analytics)
            if lines:
                rec.write({"line_ids": lines})

    def _get_context_plan_analytic(self):
        ctx = self.env.context.copy()
        ctx["default_company_ids"] = self.company_ids.ids
        return ctx

    def action_get_all_analytic_accounts(self):
        ctx = self._get_context_plan_analytic()
        return {
            "name": self.env._("Analytic Account"),
            "type": "ir.actions.act_window",
            "res_model": "budget.plan.analytic.select",
            "view_mode": "form",
            "target": "new",
            "context": ctx,
        }

    def action_confirm(self):
        # Update amount consumed and released
        self.action_update_amount_consumed()
        # Update plan line
        self.action_update_plan()
        # Check plan consumed
        self.check_plan_consumed()
        return self.write({"state": "confirm"})

    def action_done(self):
        return self.write({"state": "done"})

    def action_cancel(self):
        return self.write({"state": "cancel"})

    def action_draft(self):
        return self.write({"state": "draft"})


class BudgetPlanLine(models.Model):
    _name = "budget.plan.line"
    _description = "Budget Plan Line"
    _check_company_auto = True

    plan_id = fields.Many2one(
        comodel_name="budget.plan",
        index=True,
        ondelete="cascade",
    )
    budget_control_ids = fields.Many2many(
        comodel_name="budget.control",
        string="Related Budget Control(s)",
        compute="_compute_budget_control_ids",
        help="Note: It is intention for this field to compute in realtime",
    )
    budget_period_id = fields.Many2one(
        comodel_name="budget.period", related="plan_id.budget_period_id"
    )
    date_from = fields.Date(related="plan_id.date_from")
    date_to = fields.Date(related="plan_id.date_to")
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        required=True,
    )
    allocated_amount = fields.Monetary(string="Allocated")
    released_amount = fields.Monetary(string="Released")
    amount = fields.Monetary(string="New Amount")
    amount_consumed = fields.Monetary(string="Consumed")
    company_ids = fields.Many2many(
        comodel_name="res.company", related="analytic_account_id.budget_company_ids"
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency", related="plan_id.currency_id"
    )
    active_status = fields.Boolean(
        default=True, help="Activate/Deactivate when create/Update Budget Control"
    )

    @api.depends("analytic_account_id.budget_control_ids")
    def _compute_budget_control_ids(self):
        for rec in self.sudo():
            rec.budget_control_ids = rec.analytic_account_id.budget_control_ids

    @api.constrains("analytic_account_id")
    def _check_duplicate_analytic_account(self):
        if not self:
            return

        PlanLine = self.env["budget.plan.line"]
        analytic_ids = self.mapped("analytic_account_id.id")

        # Group by analytic_account_id and count occurrences
        duplicates = PlanLine.read_group(
            [
                ("analytic_account_id", "in", analytic_ids),
                ("plan_id", "=", self.plan_id.id),
            ],
            ["analytic_account_id"],
            ["analytic_account_id"],
        )

        # Check for duplicates
        duplicate_analytics = {
            dup["analytic_account_id"][1]
            for dup in duplicates
            if dup["analytic_account_id_count"] > 1
        }
        if duplicate_analytics:
            raise UserError(
                self.env._(f"Duplicate analytic account found: {duplicate_analytics}")
            )
