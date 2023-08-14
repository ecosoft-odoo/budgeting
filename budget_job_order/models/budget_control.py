# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class BudgetControl(models.Model):
    _inherit = "budget.control"

    filter_job_order = fields.Many2many(
        comodel_name="budget.job.order",
        relation="job_order_budget_contol_rel",
        column1="budget_control_id",
        column2="job_order_id",
        string="Filter Job Orders",
        compute="_compute_filter_job_order",
    )
    kpi_x_job_order = fields.One2many(
        comodel_name="budget.control.kpi.x.job.order",
        inverse_name="budget_control_id",
        copy=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    @api.depends("analytic_account_id")
    def _compute_filter_job_order(self):
        """Filter Job Order following Analytic Account.
        if job order is not analytic account, it mean global job order
        """
        JobOrder = self.env["budget.job.order"].search([])
        for rec in self:
            filter_job = JobOrder.filtered(
                lambda x: rec.analytic_account_id.id in x.analytic_account_ids.ids
                or not x.analytic_account_ids
            )
            rec.filter_job_order = filter_job

    def _domain_kpi_job_expression(self, dom):
        if len(dom) == 3 and dom[0] == "kpi_id.id":
            return (
                "kpi_id.id",
                "in",
                self.kpi_x_job_order.mapped("kpi_ids").ids,
            )
        return dom

    def _domain_kpi_expression(self):
        domain_kpi = super()._domain_kpi_expression()
        domain_kpi = [
            isinstance(dom, tuple) and self._domain_kpi_job_expression(dom) or dom
            for dom in domain_kpi
        ]
        return domain_kpi

    def _get_value_items(self, date_range, kpi_expression):
        """For each item, multiply by the job order"""
        items = super()._get_value_items(date_range, kpi_expression)
        if not self.kpi_x_job_order:
            return items
        # On each KPI, expand it by its job orders
        kpi_jo = {}
        for kpi_x_job in self.kpi_x_job_order:
            job_ids = kpi_x_job.job_order_ids and kpi_x_job.job_order_ids.ids or [False]
            for x in kpi_x_job.kpi_ids:
                if kpi_jo.get(x.id, False):  # same KPI, other line
                    for job in job_ids:
                        kpi_jo[x.id].append(job)
                    # delete duplicate job order in KPI
                    kpi_jo[x.id] = list(set(kpi_jo[x.id]))
                else:
                    kpi_jo[x.id] = job_ids
        new_items = []
        append = new_items.append
        for item in items:
            job_order_ids = kpi_jo.get(item["kpi_expression_id"]) or [False]
            for i, jo_id in enumerate(job_order_ids):
                new_item = item.copy()
                new_item["job_order_id"] = jo_id
                new_item["job_sequence"] = i + 1
                append(new_item)
        return new_items

    def _get_context_budget_monitoring(self):
        ctx = super()._get_context_budget_monitoring()
        ctx.update({"search_default_group_by_job_order": 1})
        return ctx

    @api.constrains("kpi_ids")
    def check_kpi_description(self):
        for rec in self:
            if rec.kpi_ids and not rec.kpi_x_job_order:
                raise UserError(_("Please fill kpis in table KPIs Description."))


class BudgetControlKPIxJobOrder(models.Model):
    _name = "budget.control.kpi.x.job.order"
    _description = "KPI x Job Order"

    budget_control_id = fields.Many2one(
        comodel_name="budget.control",
        required=True,
        index=True,
        readonly=False,
        ondelete="cascade",
    )
    mis_report_id = fields.Many2one(
        comodel_name="mis.report",
        related="budget_control_id.budget_period_id.report_id",
        readonly=True,
    )
    kpi_ids = fields.Many2many(
        comodel_name="mis.report.kpi",
        string="KPI",
        domain="[('report_id', '=', mis_report_id), ('budgetable', '=', True)]",
    )
    job_order_ids = fields.Many2many(
        comodel_name="budget.job.order",
        string="Job Orders",
    )

    @api.constrains("job_order_ids")
    def check_kpi_job(self):
        for rec in self:
            if rec.job_order_ids and not rec.kpi_ids:
                ", ".join(rec.job_order_ids.mapped("name"))
                raise UserError(_("KPI is required for Job Orders."))
