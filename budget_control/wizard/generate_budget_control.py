# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class GenerateBudgetControl(models.TransientModel):
    _name = "generate.budget.control"
    _description = "Generate Budget Control Sheets"

    budget_period_id = fields.Many2one(
        comodel_name="budget.period",
        required=True,
        default=lambda self: self._get_budget_period_id(),
        ondelete="cascade",
    )
    budget_id = fields.Many2one(
        comodel_name="mis.budget",
        related="budget_period_id.mis_budget_id",
    )
    state = fields.Selection(
        [("choose", "choose"), ("get", "get")],
        default="choose",
    )
    analytic_group_ids = fields.Many2many(
        comodel_name="account.analytic.group",
        relation="analytic_group_generate_budget_control_rel",
        column1="wizard_id",
        column2="group_id",
    )
    all_analytic_accounts = fields.Boolean(
        help="Generate budget control sheet for all missing analytic account",
    )
    analytic_account_ids = fields.Many2many(
        comodel_name="account.analytic.account",
        relation="analytic_generate_budget_control_rel",
        column1="wizard_id",
        column2="anlaytic_id",
        domain="[('group_id', 'in', analytic_group_ids)]",
    )
    init_budget_commit = fields.Boolean(
        string="Initial Budget By Commitment",
        help="If checked, the newly created budget control sheet will has "
        "initial budget equal to current budget commitment of its year.",
    )
    result_analytic_account_ids = fields.Many2many(
        comodel_name="account.analytic.account",
        relation="result_analytic_generate_budget_control_rel",
        column1="wizard_id",
        column2="anlaytic_id",
        readonly=True,
        help="Analytics not created by this operation, as they already exisits",
    )
    result_budget_control_ids = fields.Many2many(
        comodel_name="budget.control",
        relation="result_budget_generate_budget_control_rel",
        column1="wizard_id",
        column2="budget_control_id",
        readonly=True,
        help="Budget Control Sheets created by this operation",
    )

    @api.model
    def _get_budget_period_id(self):
        return self.env["budget.period"].browse(self._context.get("active_id"))

    @api.onchange("all_analytic_accounts", "analytic_group_ids")
    def _onchange_analytic_accounts(self):
        """Auto fill analytic_account_ids."""
        AnalyticAccount = self.env["account.analytic.account"]
        self.analytic_account_ids = False
        if self.all_analytic_accounts:
            self.analytic_account_ids = AnalyticAccount.search(
                [("group_id", "in", self.analytic_group_ids.ids)]
            )

    def _prepare_value_duplicate(self, vals):
        plan_date_range_id = self.budget_period_id.plan_date_range_type_id.id
        budget_id = self.budget_id.id
        budget_name = self.budget_period_id.name
        return list(
            map(
                lambda l: {
                    "name": "{} :: {}".format(
                        budget_name, l["analytic_account_id"].name
                    ),
                    "budget_id": budget_id,
                    "analytic_account_id": l["analytic_account_id"].id,
                    "plan_date_range_type_id": plan_date_range_id,
                },
                vals,
            )
        )

    def _prepare_value(self, analytic):
        return [{"analytic_account_id": x} for x in analytic]

    def _prepare_budget_control_sheet(self, analytic):
        vals = self._prepare_value(analytic)
        return self._prepare_value_duplicate(vals)

    def _get_existing_budget(self):
        BudgetControl = self.env["budget.control"]
        existing_budget = BudgetControl.search(
            [
                ("budget_id", "=", self.budget_id.id),
                ("analytic_account_id", "in", self.analytic_account_ids.ids),
            ]
        )
        return existing_budget

    def _hook_budget_controls(self, budget_controls):
        return budget_controls

    def _create_budget_controls(self, vals):
        return self.env["budget.control"].create(vals)

    def action_generate_budget_control(self):
        """Create new draft budget control sheet for all selected analytics."""
        self.ensure_one()
        # Find existing controls, so we can skip.
        existing_budget = self._get_existing_budget()
        existing_analytics = existing_budget.mapped("analytic_account_id")
        # Create budget controls that are not already exists
        new_analytic = self.analytic_account_ids - existing_analytics
        vals = self._prepare_budget_control_sheet(new_analytic)
        budget_controls = self._create_budget_controls(vals)
        # Update budget control in analytic
        for bc in budget_controls:
            bc.analytic_account_id.write({"budget_control_id": bc.id})
        budget_controls = self._hook_budget_controls(budget_controls)
        budget_controls.do_init_budget_commit(self.init_budget_commit)
        # Return result
        self.write(
            {
                "state": "get",
                "result_analytic_account_ids": [
                    (6, 0, existing_analytics.ids)
                ],
                "result_budget_control_ids": [(6, 0, budget_controls.ids)],
            }
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "form",
            "view_type": "form",
            "res_id": self.id,
            "views": [(False, "form")],
            "target": "new",
        }

    def action_view_budget_control(self):
        self.ensure_one()
        action = self.env.ref("budget_control.budget_control_action")
        result = action.read()[0]
        result["domain"] = [("id", "in", self.result_budget_control_ids.ids)]
        return result
