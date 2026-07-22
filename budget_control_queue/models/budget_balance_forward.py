# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models

from odoo.addons.queue_job.delay import group


class BudgetBalanceForward(models.Model):
    _inherit = "budget.balance.forward"

    use_queue_job = fields.Boolean()
    still_running = fields.Boolean(copy=False)

    def _create_missing_analytic_job(self, lines):
        self.ensure_one()
        for line in lines:
            line.to_analytic_account_id = line.analytic_account_id.next_year_analytic()

    def create_missing_analytic(self):
        if not self.use_queue_job:
            return super().create_missing_analytic()

        ICP = self.env["ir.config_parameter"]
        chunk_size_create_analytic = (
            int(ICP.sudo().get_param("budget_control.forward_create_analytic")) or 100
        )

        for rec in self:
            lines = rec.forward_line_ids.filtered_domain(
                [("to_analytic_account_id", "=", False)]
            )
            job_create_missing = []
            # Create analytic with chunk
            for i in range(0, len(lines), chunk_size_create_analytic):
                chunk_lines = lines[i : i + chunk_size_create_analytic]
                job1 = rec.delayable(
                    channel="root.budget_forward"
                )._create_missing_analytic_job(chunk_lines)
                job_create_missing.append(job1)
            # Change state and still running flag
            rec.write({"still_running": True})
            # Job delay, change state back to done
            job_run_done = rec.delayable(channel="root.budget_forward").write(
                {"still_running": False}
            )

            # Run queue job
            group_job_create_missing = group(*job_create_missing)
            group_job_create_missing.on_done(job_run_done)
            group_job_create_missing.delay()

    def _action_budget_balance_forward(self):
        for rec in self:
            for line in rec.forward_line_ids:
                if line.method_type == "extend":
                    line.to_analytic_account_id.bm_date_to = (
                        rec.to_budget_period_id.bm_date_to
                    )
        # --
        self.write({"state": "done"})

    def action_budget_balance_forward(self):
        if not self.use_queue_job:
            return super().action_budget_balance_forward()

        job_balance_forward = self.delayable(
            channel="root.budget_forward"
        )._action_budget_balance_forward()
        # Change state and still running flag
        self.write({"still_running": True})
        # Job delay, change state back to done
        job_run_done = self.delayable(channel="root.budget_forward").write(
            {"still_running": False}
        )

        # Run queue job
        job_balance_forward.on_done(job_run_done)
        job_balance_forward.delay()
