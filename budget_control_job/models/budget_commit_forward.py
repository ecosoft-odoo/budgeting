# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models


class BudgetCommitForward(models.Model):
    _inherit = "budget.commit.forward"

    job_uuid = fields.Char(
        string="Job UUID",
        readonly=True,
    )
    is_done = fields.Boolean(readonly=True)

    def action_budget_commit_forward_job(self):
        description = _("Creating forward commit budget with id %s") % (self.id,)
        job = self.with_delay(description=description).action_budget_commit_forward()
        # Update UUID in forward commit
        self.job_uuid = job.uuid
        return "Job created with uuid {}".format(job.uuid)

    def action_budget_commit_forward(self):
        """Overwrite function recompute"""
        self._do_forward_commit()
        self.write({"state": "done"})
        self._do_update_initial_commit()
        # Recompute budget on document number
        documents = []
        for line in self.forward_line_ids:
            if line.is_done:
                continue
            doc = line.document_number
            if doc not in documents:
                doc.recompute_budget_move()
                documents.append(doc)
            line.is_done = True
            self.env.cr.commit()
        if all(line.is_done for line in self.forward_line_ids):
            self.is_done = True


class BudgetCommitForwardLine(models.Model):
    _inherit = "budget.commit.forward.line"

    is_done = fields.Boolean(readonly=True)
