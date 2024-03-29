# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MisBudgetItem(models.Model):
    _inherit = "mis.budget.item"
    _order = "date_range_id, job_order_id, kpi_expression_id"

    job_order_id = fields.Many2one(
        comodel_name="budget.job.order",
        ondelete="cascade",
        index=True,
    )
    job_sequence = fields.Integer(
        default=1,
        help="This field help check same KPIs, diff job order",
    )

    def _prepare_overlap_domain(self):
        domain = super()._prepare_overlap_domain()
        domain.extend(
            [
                ("job_order_id", "=", self.job_order_id.id),
                ("job_sequence", "=", self.job_sequence),
            ]
        )
        return domain

    def _compute_name(self):
        """Adding Job Order"""
        super()._compute_name()
        for rec in self.filtered("job_order_id"):
            rec.name = "{} / {}".format(rec.job_order_id.name, rec.name)

    def search_neutralize(self, dom):
        mis_filter = self._context.get("mis_report_filters", {})
        if mis_filter and len(dom) == 3 and dom[0] == "job_order_id":
            return (1, "=", 1)
        return super().search_neutralize(dom)
