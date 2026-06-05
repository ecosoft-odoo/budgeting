# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models

from odoo.addons.queue_job.delay import chain, group


class BudgetCommitForward(models.Model):
    _inherit = "budget.commit.forward"

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
            int(ICP.sudo().get_param("budget_control.carry_forward_create_analytic"))
            or 100
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

    def _job_do_forward_commit(self):
        self._do_forward_commit()
        self.write({"state": "done"})
        self._do_update_initial_commit()

    def _job_recompute(self, chunk_lines):
        for line in chunk_lines:
            doc = line.document_number
            doc.recompute_budget_move()

    def action_budget_commit_forward(self):
        """Use queue job will split function into multiple jobs"""
        if not self.use_queue_job:
            return super().action_budget_commit_forward()

        ICP = self.env["ir.config_parameter"]
        chunk_size_carry_forward = (
            int(ICP.sudo().get_param("budget_control.carry_forward")) or 10
        )

        # Job1: Do Forward Commit
        job_carry_commit = self.delayable(
            channel="root.budget_forward"
        )._job_do_forward_commit()

        # Recompute budget on document number
        job_recompute = []
        lines = self.forward_line_ids
        for i in range(0, len(lines), chunk_size_carry_forward):
            chunk_lines = lines[i : i + chunk_size_carry_forward]

            # Job2: Recompute after carry forward and update line is done
            job2 = self.delayable(channel="root.budget_forward")._job_recompute(
                chunk_lines
            )
            job_recompute.append(job2)
        self.write({"still_running": True})

        group_job_recompute = group(*job_recompute)

        # Job3: Update header is done
        job_run_done = self.delayable(channel="root.budget_forward").write(
            {"still_running": False}
        )

        # Run queue job
        chain_process = chain(
            job_carry_commit,
            group_job_recompute,
            job_run_done,
        )
        chain_process.delay()

    def _job_reverse_forward_commit(self):
        self.filtered(lambda l: l.state == "done")._do_forward_commit(reverse=True)
        self.write({"state": "cancel"})
        self._do_update_initial_commit(reverse=True)

    def _action_cancel(self):
        """Use queue job will split function into multiple jobs"""
        if not self.use_queue_job:
            return super()._action_cancel()

        ICP = self.env["ir.config_parameter"]
        chunk_size_carry_forward_cancel = (
            int(ICP.sudo().get_param("budget_control.carry_forward")) or 10
        )

        # Job1: Reverse Forward Commit
        job_carry_commit = self.delayable(
            channel="root.budget_forward"
        )._job_reverse_forward_commit()

        # Recompute budget on document number
        job_recompute = []
        lines = self.forward_line_ids
        for i in range(0, len(lines), chunk_size_carry_forward_cancel):
            chunk_lines = lines[i : i + chunk_size_carry_forward_cancel]

            # Job2: Recompute after carry forward and update line is done
            job2 = self.delayable(channel="root.budget_forward")._job_recompute(
                chunk_lines
            )
            job_recompute.append(job2)
        self.write({"still_running": True})

        group_job_recompute = group(*job_recompute)

        # Job3: Update header is done
        job_run_done = self.delayable(channel="root.budget_forward").write(
            {"still_running": False}
        )

        # Run queue job
        chain_process = chain(
            job_carry_commit,
            group_job_recompute,
            job_run_done,
        )
        chain_process.delay()
