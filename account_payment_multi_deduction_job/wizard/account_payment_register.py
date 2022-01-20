# Copyright 2021 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    deduct_job_order_id = fields.Many2one(
        comodel_name="budget.job.order",
        compute="_compute_default_job_order",
    )

    def _get_job_order_lines(self):
        active_ids = self.env.context.get("active_ids", [])
        moves = self.env["account.move"].browse(active_ids)
        move_lines = moves.mapped("line_ids")
        job_order = move_lines.mapped("job_order_id")
        return job_order

    @api.depends("payment_difference", "deduction_ids")
    def _compute_default_job_order(self):
        job_order = self._get_job_order_lines()
        for rec in self:
            rec.deduct_job_order_id = (
                len(job_order) == 1 and job_order.id or False
            )

    @api.onchange("payment_difference", "payment_difference_handling")
    def _onchange_default_job_order(self):
        if self.payment_difference_handling == "reconcile":
            job_order = self._get_job_order_lines()
            self.job_order_id = len(job_order) == 1 and job_order.id or False

    def _prepare_deduct_move_line(self, deduct):
        vals = super()._prepare_deduct_move_line(deduct)
        vals.update(
            {
                "job_order_id": deduct.job_order_id
                and deduct.job_order_id.id
                or False
            }
        )
        return vals

    def _create_payment_vals_from_wizard(self):
        payment_vals = super()._create_payment_vals_from_wizard()
        if (
            not self.currency_id.is_zero(self.payment_difference)
            and self.payment_difference_handling == "reconcile"
        ):
            payment_vals["write_off_line_vals"][
                "job_order_id"
            ] = self.job_order_id.id
        return payment_vals
