# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError


class BudgetPlan(models.Model):
    _name = "budget.plan"
    _inherit = ["budget.plan", "base.revision"]

    current_revision_id = fields.Many2one(
        comodel_name="budget.plan",
    )
    old_revision_ids = fields.One2many(
        comodel_name="budget.plan",
    )
    init_revision = fields.Boolean(
        compute="_compute_init_revision",
        store=True,
    )

    @api.depends("revision_number")
    def _compute_init_revision(self):
        for rec in self:
            rec.init_revision = not rec.revision_number

    def _query_budget_controls_revision(self, domain_analytics, date_from, date_to):
        """Find revisions of budget_controls, and use latest one to create_revision()"""
        query = f"""
            SELECT bc.id
            FROM budget_control bc
            JOIN budget_period bp ON bp.id = bc.budget_period_id
            WHERE bc.analytic_account_id {domain_analytics}
            AND bp.bm_date_from <= %s
            AND bp.bm_date_to >= %s
            AND bc.revision_number = (
                SELECT max(revision_number)
                FROM budget_control bc
                JOIN budget_period bp ON bp.id = bc.budget_period_id
                WHERE bc.analytic_account_id {domain_analytics}
                AND bp.bm_date_from <= %s
                AND bp.bm_date_to >= %s
            )
        """
        self.env.cr.execute(
            query,
            (
                self.budget_period_id.bm_date_from,
                self.budget_period_id.bm_date_to,
                self.budget_period_id.bm_date_from,
                self.budget_period_id.bm_date_to,
            ),
        )
        return [bc[0] for bc in self.env.cr.fetchall()]

    def action_create_update_budget_control(self):
        """Update budget control to version lastest.
        if add new analytic or amount with same revision,
        it will call main function action_create_update_budget_control() only.
        """
        self = self.with_context(active_test=False)
        no_bc_lines = self.line_ids.filtered_domain(
            [("budget_control_ids", "=", False)]
        )
        # Case new no link between budget plan line and budget control
        if no_bc_lines:
            analytics = no_bc_lines.mapped("analytic_account_id")
            if len(analytics) > 1:
                domain_analytics = f"in {tuple(analytics.ids)}"
            else:
                domain_analytics = f"= {analytics.id}"
            budget_control_ids = self._query_budget_controls_revision(
                domain_analytics,
                self.budget_period_id.bm_date_from,
                self.budget_period_id.bm_date_to,
            )
            budget_controls = self.env["budget.control"].browse(budget_control_ids)
        else:
            revision = self.revision_number
            # Get only revision is not equal
            budget_controls = self.budget_control_ids.filtered(
                lambda bc, revision=revision: bc.revision_number != revision
            )

        # Auto cancel budget control
        if self.env.company.budget_plan_revision_cancel == "auto":
            budget_controls.action_cancel()
        budget_controls.invalidate_recordset()

        # Check state budget control
        if any(bc.state != "cancel" for bc in budget_controls):
            raise UserError(
                self.env._(
                    "In order to create new budget control version, "
                    "all current ones must be cancelled."
                )
            )
        for bc in budget_controls.with_context(revision_number=self.revision_number):
            bc.create_revision()
        return super(
            BudgetPlan,
            self.with_context(revision_number=self.revision_number),
        ).action_create_update_budget_control()

    def create_revision(self):
        """Not allow revise, if not budget control"""
        if any(not rec.budget_control_count for rec in self):
            raise UserError(
                self.env._(
                    "Cannot revise budget plan that is not related to budget control."
                )
            )
        return super().create_revision()


class BudgetPlanLine(models.Model):
    _inherit = "budget.plan.line"

    revision_number = fields.Integer(related="plan_id.revision_number")

    @api.depends("analytic_account_id.budget_control_ids")
    def _compute_budget_control_ids(self):
        """Overwrite to get budget control from revision"""
        for rec in self.sudo():
            revision = rec.plan_id.revision_number
            rec.budget_control_ids = (
                rec.analytic_account_id.budget_control_ids.filtered(
                    lambda bc, revision=revision: bc.revision_number == revision
                )
            )
