# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
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
    init_revision = fields.Boolean(default=True, readonly=True)

    def _query_budget_controls_revision(self, domain_analytics, date_from, date_to):
        """Find revisions of budget_controls, and use latest one to create_revision()"""
        cr = self._cr
        query = """
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
        """.format(
            domain_analytics=domain_analytics
        )
        cr.execute(
            query,
            (
                self.budget_period_id.bm_date_from,
                self.budget_period_id.bm_date_to,
                self.budget_period_id.bm_date_from,
                self.budget_period_id.bm_date_to,
            ),
        )
        return [bc[0] for bc in cr.fetchall()]

    def action_create_update_budget_control(self):
        """Update budget control to version lastest"""
        self = self.with_context(active_test=False)
        no_bc_lines = self.line_ids.filtered_domain(
            [("budget_control_ids", "=", False)]
        )
        analytics = no_bc_lines.mapped("analytic_account_id")
        if len(analytics) > 1:
            domain_analytics = "in {}".format(tuple(analytics.ids))
        else:
            domain_analytics = "= {}".format(analytics.id)
        budget_control_ids = self._query_budget_controls_revision(
            domain_analytics,
            self.budget_period_id.bm_date_from,
            self.budget_period_id.bm_date_to,
        )
        budget_controls = self.env["budget.control"].browse(budget_control_ids)
        # Check state budget control for user manual cancel.
        if any(bc.state != "cancel" for bc in budget_controls):
            raise UserError(
                _(
                    "In order to create new budget control version, "
                    "all current ones must be cancelled."
                )
            )
        for bc in budget_controls.with_context(revision_number=self.revision_number):
            bc.create_revision()
        return super(
            BudgetPlan,
            self.with_context(
                revision_number=self.revision_number,
                init_revision=self.init_revision,
            ),
        ).action_create_update_budget_control()

    def _get_new_rev_data(self, new_rev_number):
        """Update revision budget plan is not initial revision"""
        self.ensure_one()
        new_rev_dict = super()._get_new_rev_data(new_rev_number)
        new_rev_dict["init_revision"] = False
        return new_rev_dict

    def create_revision(self):
        """Create budget plan revision and all its budget controls"""
        # Not allow revise, if not budget control
        if any(not rec.budget_control_count for rec in self):
            raise UserError(
                _("Cannot revise budget plan that is not related to budget control.")
            )
        return super().create_revision()


class BudgetPlanLine(models.Model):
    _inherit = "budget.plan.line"

    revision_number = fields.Integer(related="plan_id.revision_number")

    def _domain_budget_control(self):
        domain = super()._domain_budget_control()
        domain.extend([("revision_number", "=", self.revision_number)])
        return domain

    def _find_budget_controls(self):
        """For case new revision budget plan and not create budget control yet,
        it should get budget control from old version"""
        if not (self.plan_id.init_revision or self.budget_control_ids):
            domain_analytics = "= {}".format(self.analytic_account_id.id)
            budget_control_id = self.plan_id._query_budget_controls_revision(
                domain_analytics,
                self.budget_period_id.bm_date_from,
                self.budget_period_id.bm_date_to,
            )
            budget_controls = self.env["budget.control"].browse(budget_control_id)
            return budget_controls
        return super()._find_budget_controls()
