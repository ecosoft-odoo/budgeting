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
            for kpi in rec.kpi_ids:
                rec.kpi_x_job_order += KPIxJO.new(
                    {
                        "kpi_ids": [kpi.id],
                        "job_order_ids": rec.job_order_ids.ids,
                    }
                )

    def _get_value_items(self, date_range, kpi_expression):
        """ For each item, multiply by the job order """
        items = super()._get_value_items(date_range, kpi_expression)
        if not self.kpi_x_job_order:
            return items
        # On each KPI, expand it by its job orders
        kpi_jo = {
            x.kpi_ids[0].id: x.job_order_ids.ids for x in self.kpi_x_job_order
        }
        new_items = []
        for item in items:
            job_order_ids = kpi_jo.get(item["kpi_expression_id"]) or [False]
            for jo_id in job_order_ids:
                new_item = item.copy()
                new_item["job_order_id"] = jo_id
                new_items.append(new_item)
        return new_items


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
    kpi_ids = fields.Many2many(
        comodel_name="mis.report.kpi",
        string="KPI",
        readonly=True,
    )
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        related="budget_control_id.analytic_account_id",
    )
    job_order_ids = fields.Many2many(
        comodel_name="budget.job.order",
        string="Job Orders",
        domain="[('analytic_account_id', '=', analytic_account_id)]",
    )
