# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class BudgetControl(models.Model):
    _inherit = "budget.control"

    use_all_job_order = fields.Boolean(string="Use All Job Orders")
    job_order_ids = fields.Many2many(
        string="Job Orders",
        comodel_name="budget.job.order",
        relation="job_order_budget_contol_rel",
        column1="budget_control_id",
        column2="job_order_id",
        domain="[('analytic_account_id', '=', analytic_account_id)]",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    kpi_x_job_order = fields.One2many(
        comodel_name="budget.control.kpi.x.job.order",
        inverse_name="budget_control_id",
        copy=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

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
            isinstance(dom, tuple)
            and self._domain_kpi_job_expression(dom)
            or dom
            for dom in domain_kpi
        ]
        return domain_kpi

    @api.onchange("use_all_job_order")
    def _onchange_use_all_job_order(self):
        if self.use_all_job_order:
            domain = [
                ("analytic_account_id", "=", self.analytic_account_id.id)
            ]
            self.job_order_ids = self.env["budget.job.order"].search(domain)
        else:
            self.job_order_ids = False

    @api.onchange("kpi_ids", "job_order_ids")
    def _compute_kpi_x_job_order(self):
        KPIxJO = self.env["budget.control.kpi.x.job.order"]
        for rec in self:
            rec.kpi_x_job_order = False
            for job in rec.job_order_ids:
                rec.kpi_x_job_order += KPIxJO.new(
                    {
                        "job_order_ids": [job.id],
                        "kpi_ids": rec.kpi_ids.ids,
                    }
                )

    def _get_value_items(self, date_range, kpi_expression):
        """ For each item, multiply by the job order """
        items = super()._get_value_items(date_range, kpi_expression)
        if not self.kpi_x_job_order:
            return items
        # On each KPI, expand it by its job orders
        kpi_jo = {}
        for kpi_x_job in self.kpi_x_job_order:
            job_id = (
                kpi_x_job.job_order_ids
                and kpi_x_job.job_order_ids[0].id
                or False
            )
            for x in kpi_x_job.kpi_ids:
                if kpi_jo.get(x.id, False):
                    kpi_jo[x.id].append(job_id)
                else:
                    kpi_jo[x.id] = [job_id]
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
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        related="budget_control_id.analytic_account_id",
    )
    job_order_ids = fields.Many2many(
        comodel_name="budget.job.order",
        string="Job Orders",
        readonly=True,
    )
