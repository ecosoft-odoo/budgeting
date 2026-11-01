# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class BudgetCommonMonitoring(models.AbstractModel):
    _name = "budget.common.monitoring"
    _description = "Budget Common Monitoring"

    res_id = fields.Reference(
        selection=lambda self: (
            [("budget.control.line", "Budget Control Lines")]
            + [("budget.balance.forward.line", "Budget Balance Forward Line")]
            + self._get_budget_docline_model()
        ),
        string="Resource ID",
    )
    reference = fields.Char()
    amount_type = fields.Selection(
        selection=lambda self: (
            [("10_budget", "Budget")]
            + [("12_forward_out", "Forward Balance Out")]
            + self._get_budget_amount_type()
        ),
        string="Type",
    )
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
    )
    budget_period_id = fields.Many2one(
        comodel_name="budget.period",
    )
    active = fields.Boolean()
    amount = fields.Float()

    @api.model
    def _read_group_dataset(self, domain, fields, groupby):
        """Group monitoring rows, returning one dict per group with
        many2one values as ``(id, display_name)`` and summed amounts,
        i.e. the format of ``read_group(..., lazy=False)`` before 19.0."""
        aggregates = [f"{fname}:sum" for fname in fields if fname not in groupby]
        dataset = []
        for row in self._read_group(domain, groupby, aggregates):
            data = {}
            for fname, value in zip(groupby, row, strict=False):
                if isinstance(value, models.BaseModel):
                    value = (value.id, value.display_name) if value else False
                data[fname] = value
            for spec, value in zip(aggregates, row[len(groupby) :], strict=True):
                data[spec.split(":")[0]] = value
            dataset.append(data)
        return dataset

    def _get_budget_amount_type(self):
        """Return list of all amount_type selection, in the order of their
        keys: the monitoring shows commitments before actuals."""
        return sorted(x["type"] for x in self._get_consumed_sources())

    def _get_budget_docline_model(self):
        """Return list of all res_id models selection"""
        return [x["model"] for x in self._get_consumed_sources()]

    def _get_consumed_sources(self):
        return [
            {
                "model": ("account.move.line", "Account Move Line"),
                "type": ("80_actual", "Actual"),
                "budget_move": ("account_budget_move", "move_line_id"),
                "source_doc": ("account_move", "move_id"),
            }
        ]
