# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, format_amount

from odoo.addons.budget_control.models.analytic_plan import BUDGET_COLUMN


class BudgetPlanLineDetail(models.Model):
    """The allocation of a plan line by dimension, e.g. Department 1 gets 100
    from Fund A and 50 from Fund B: the line sums them, and its budget control
    sheet stays one for the analytic account."""

    _name = "budget.plan.line.detail"
    _description = "Budget Plan Line Detail"
    _order = "plan_line_id, id"
    # Users enter the dimension accounts of the budget analytic of the line
    _budget_plan_columns_readonly = False

    plan_line_id = fields.Many2one(
        comodel_name="budget.plan.line",
        required=True,
        index=True,
        ondelete="cascade",
    )
    plan_id = fields.Many2one(
        comodel_name="budget.plan",
        related="plan_line_id.plan_id",
        store=True,
        index=True,
    )
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        related="plan_line_id.analytic_account_id",
        store=True,
        index=True,
    )
    amount = fields.Monetary(string="Allocated")
    company_ids = fields.Many2many(
        comodel_name="res.company", related="plan_id.company_ids"
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency", related="plan_id.currency_id"
    )
    amount_consumed = fields.Monetary(
        string="Consumed",
        compute="_compute_amount_consumed",
        compute_sudo=True,
        help="Commitments and actuals of the allocation in the period of the plan.",
    )
    amount_available = fields.Monetary(
        string="Available",
        compute="_compute_amount_consumed",
        compute_sudo=True,
    )

    @api.model
    def _get_view(self, view_id=None, view_type="form", **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        self.env["account.analytic.plan"]._patch_budget_plan_view(
            arch, view_type, self._name
        )
        return arch, view

    def _get_budget_plan_fnames(self):
        """Plan columns of details, in the order of their plans."""
        return sorted(
            (fname for fname in self._fields if BUDGET_COLUMN.fullmatch(fname)),
            key=lambda fname: int(BUDGET_COLUMN.fullmatch(fname).group(1)),
        )

    def _get_dimension_fnames(self):
        """Plan columns set on these details: their dimensions."""
        return [
            fname
            for fname in self._get_budget_plan_fnames()
            if any(rec[fname] for rec in self)
        ]

    def _get_dimensions(self, fnames):
        self.ensure_one()
        return tuple((fname, self[fname].id) for fname in fnames)

    @api.model
    def _get_budget_name(self, analytic, dimensions):
        """Name of the budget of ``analytic`` for ``dimensions``,
        ``((fname, account id), ...)``, e.g. "Department 1 / Fund A"."""
        accounts = analytic.browse(
            [account_id for _fname, account_id in dimensions if account_id]
        )
        return " / ".join([analytic.display_name, *accounts.mapped("display_name")])

    @api.model
    def _get_dimensions_name(self, dimensions):
        """Name of ``dimensions`` alone, e.g. "Fund A"."""
        accounts = self.env["account.analytic.account"].browse(
            [account_id for _fname, account_id in dimensions if account_id]
        )
        return " / ".join(accounts.mapped("display_name")) or self.env._("No account")

    @api.model
    def _get_budget_consumptions(self, budget_period, analytic, fnames):
        """Commitments and actuals of ``analytic`` in ``budget_period`` by
        dimension, ``{((fname, account id), ...): amount}``, negative amounts as
        in the monitoring."""
        if not budget_period or not analytic:
            return {}
        # The monitoring is a view of the budget moves
        self.env.flush_all()
        groups = (
            self.env["budget.monitor.report"]
            .sudo()
            ._read_group(
                [
                    ("analytic_account_id", "=", analytic.id),
                    ("budget_period_id", "=", budget_period.id),
                    ("amount_type", "not in", ("10_budget", "12_forward_out")),
                ],
                list(fnames),
                ["amount:sum"],
            )
        )
        return {
            tuple(
                (fname, account.id)
                for fname, account in zip(fnames, group[:-1], strict=True)
            ): group[-1]
            for group in groups
        }

    @api.depends(
        lambda self: ["amount", "plan_line_id", *self._get_budget_plan_fnames()]
    )
    def _compute_amount_consumed(self):
        consumptions = {}
        for detail in self:
            line = detail.plan_line_id
            fnames = tuple(line.detail_ids._get_dimension_fnames())
            key = (line.budget_period_id, line.analytic_account_id, fnames)
            if key not in consumptions:
                consumptions[key] = self._get_budget_consumptions(*key)
            consumed = -consumptions[key].get(detail._get_dimensions(fnames), 0.0)
            detail.amount_consumed = consumed
            detail.amount_available = detail.amount - consumed

    @api.constrains("amount")
    def _check_amount_nonnegative(self):
        for rec in self:
            if (
                float_compare(
                    rec.amount, 0.0, precision_rounding=rec.currency_id.rounding
                )
                < 0
            ):
                raise ValidationError(self.env._("Allocated cannot be negative."))

    @api.constrains(
        lambda self: ["plan_line_id", "amount", *self._get_budget_plan_fnames()]
    )
    def _check_plan_line_details(self):
        # Lines check their details once all are written
        if not self.env.context.get("budget_plan_line_details"):
            self.plan_line_id._check_details()

    def write(self, vals):
        if "plan_line_id" in vals and any(
            rec.plan_line_id.id != vals["plan_line_id"] for rec in self
        ):
            raise UserError(self.env._("Details cannot move to another plan line."))
        return super().write(vals)

    def unlink(self):
        lines = self.plan_line_id
        res = super().unlink()
        if not self.env.context.get("budget_plan_line_details"):
            lines = lines.exists()
            lines._check_detail_consumptions()
            lines.filtered(lambda line: not line.detail_ids)._check_details_kept()
        return res

    @api.model
    def _get_budget_allocations(self, budget_period, analytic):
        """Details of ``analytic`` in the plan managing its budget control
        sheet of ``budget_period``, see budget.control._get_budget_allocations()."""
        control = (
            self.env["budget.control"]
            .sudo()
            .search(
                [
                    ("budget_period_id", "=", budget_period.id),
                    ("analytic_account_id", "=", analytic.id),
                    ("active", "=", True),
                    ("state", "!=", "cancel"),
                ],
                limit=1,
            )
        )
        return control._get_budget_allocations() if control else self.browse()

    @api.model
    def _check_budget_allocation(self, budget_period, budget_moves):
        """Messages for the ``budget_moves`` of ``budget_period`` that charge
        an analytic account allocated by dimension outside its allocations,
        or over them with the commitments and actuals of the period."""
        messages = []
        for analytic, moves in budget_moves.grouped("analytic_account_id").items():
            allocations = self._get_budget_allocations(budget_period, analytic)
            if not allocations:
                continue
            fnames = allocations._get_dimension_fnames()
            details_by_dimensions = allocations.grouped(
                lambda detail, fnames=fnames: detail._get_dimensions(fnames)
            )
            consumptions = self._get_budget_consumptions(
                budget_period, analytic, fnames
            )
            budgets = {
                tuple((fname, move[fname].id) for fname in fnames) for move in moves
            }
            for dimensions in sorted(budgets):
                name = self._get_budget_name(analytic, dimensions)
                details = details_by_dimensions.get(dimensions)
                if not details:
                    messages.append(
                        self.env._(
                            "%(budget)s is not allocated in %(period)s.",
                            budget=name,
                            period=budget_period.display_name,
                        )
                    )
                    continue
                balance = sum(details.mapped("amount")) + consumptions.get(
                    dimensions, 0.0
                )
                currency = details.currency_id[:1] or self.env.company.currency_id
                if (
                    float_compare(balance, 0.0, precision_rounding=currency.rounding)
                    < 0
                ):
                    messages.append(
                        self.env._(
                            "%(budget)s allocation, will result in %(balance)s",
                            budget=name,
                            balance=format_amount(self.env, balance, currency),
                        )
                    )
        return messages
