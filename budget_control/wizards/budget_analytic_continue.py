# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import format_date


class BudgetAnalyticContinue(models.TransientModel):
    _name = "budget.analytic.continue"
    _description = "Continue Analytics in a Budget Period"

    budget_period_id = fields.Many2one(
        comodel_name="budget.period",
        required=True,
        domain=[("budget_scope", "=", "fiscal")],
        help="Period the analytics continue in, e.g. the next year.",
    )
    analytic_ids = fields.Many2many(
        comodel_name="account.analytic.account",
        string="Analytics",
    )
    line_ids = fields.One2many(
        comodel_name="budget.analytic.continue.line",
        inverse_name="wizard_id",
        string="Lines",
    )

    @api.model
    def _get_continue_action(self, budget_period, analytics):
        """Action continuing ``analytics`` in ``budget_period``."""
        return {
            "name": self.env._("Continue in %s", budget_period.display_name),
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_budget_period_id": budget_period.id,
                "default_analytic_ids": [Command.set(analytics.ids)],
            },
        }

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        context = self.env.context
        if (
            "analytic_ids" in fields_list
            and not res.get("analytic_ids")
            and context.get("active_model") == "account.analytic.account"
        ):
            res["analytic_ids"] = [Command.set(context.get("active_ids", []))]
        return res

    @api.model_create_multi
    def create(self, vals_list):
        wizards = super().create(vals_list)
        for wizard in wizards.filtered(lambda wizard: not wizard.line_ids):
            wizard.line_ids = [
                Command.create(vals) for vals in wizard._prepare_line_vals()
            ]
        return wizards

    @api.onchange("budget_period_id", "analytic_ids")
    def _onchange_line_ids(self):
        self.line_ids = [Command.clear()] + [
            Command.create(vals) for vals in self._prepare_line_vals()
        ]

    def _prepare_line_vals(self):
        """One line for each analytic that does not continue in the period
        yet, from where it continues so far, e.g. the analytic of a period
        before: a continuing analytic, without Budget Period, is extended; a
        yearly one continues as the only analytic of the period matching it,
        or as a new copy."""
        self.ensure_one()
        period = self.budget_period_id
        if not period:
            return []
        vals_list = []
        lasts = self.env["account.analytic.account"]
        for source in self.analytic_ids:
            if (
                source.budget_control_scope == "lifetime"
                or source._get_forward_analytic(period)
            ):
                continue
            # No loop: see _check_next_analytic()
            analytic = source
            while analytic.next_analytic_id:
                analytic = analytic.next_analytic_id
            if analytic in lasts:
                continue
            lasts |= analytic
            next_analytic = analytic.browse()
            if not analytic.budget_period_id:
                action = "extend" if analytic.bm_date_to else "link"
            else:
                matches = analytic._get_next_analytic_matches(period)
                action = "link" if matches else "create"
                if len(matches) == 1:
                    next_analytic = matches
            vals_list.append(
                {
                    "analytic_account_id": analytic.id,
                    "action": action,
                    "next_analytic_id": next_analytic.id,
                }
            )
        return vals_list

    def action_confirm(self):
        self.ensure_one()
        period = self.budget_period_id
        for line in self.line_ids:
            analytic = line.analytic_account_id
            if line.action == "extend":
                analytic._extend_budget_analytic(period)
            elif line.action == "create":
                analytic.next_analytic_id = analytic.copy(
                    analytic._prepare_next_analytic_vals(period)
                )
            elif line.next_analytic_id:
                analytic.next_analytic_id = line.next_analytic_id
            else:
                raise UserError(
                    self.env._(
                        "Choose the analytic %s continues as.", analytic.display_name
                    )
                )
            if not analytic._get_forward_analytic(period):
                raise UserError(
                    self.env._(
                        "%(analytic)s still does not continue in %(period)s: it "
                        "continues as an analytic of another period, or one closed "
                        "on %(date)s.",
                        analytic=analytic.display_name,
                        period=period.display_name,
                        date=format_date(self.env, period.bm_date_from),
                    )
                )
        self._refresh_forward_targets()
        return {"type": "ir.actions.act_window_close"}

    def _refresh_forward_targets(self):
        """The lines of open forwards without forward analytic take where
        their analytics continue now, e.g. once a later analytic of their
        chain continues: they depend on the next analytic of their own
        analytic only."""
        for model in ("budget.commit.forward.line", "budget.balance.forward.line"):
            lines = self.env[model].search(
                [
                    ("to_analytic_account_id", "=", False),
                    ("forward_id.state", "in", ("draft", "review")),
                ]
            )
            for line in lines:
                line.to_analytic_account_id = (
                    line.analytic_account_id._get_forward_analytic(
                        line.forward_id.to_budget_period_id
                    )
                )


class BudgetAnalyticContinueLine(models.TransientModel):
    _name = "budget.analytic.continue.line"
    _description = "Analytic to Continue in a Budget Period"

    wizard_id = fields.Many2one(
        comodel_name="budget.analytic.continue",
        required=True,
        ondelete="cascade",
    )
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Analytic",
        required=True,
        readonly=True,
    )
    budget_period_id = fields.Many2one(
        related="analytic_account_id.budget_period_id",
        string="Analytic Period",
    )
    action = fields.Selection(
        selection=[
            ("link", "Continue As"),
            ("create", "Create Next Analytic"),
            ("extend", "Extend"),
        ],
        required=True,
        help="Continue As: an existing analytic of the period.\n"
        "Create Next Analytic: a copy of the analytic for the period.\n"
        "Extend: the analytic, without Budget Period, stays open to the end of "
        "the period.",
    )
    next_analytic_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Continues As",
        domain="[('id', '!=', analytic_account_id), ('control_budget', '=', True), "
        "('budget_control_scope', '=', 'fiscal')]",
    )
