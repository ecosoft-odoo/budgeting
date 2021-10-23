# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class BudgetPeriod(models.Model):
    _inherit = "budget.period"

    contract = fields.Boolean(
        string="On Contract (non-recurring)",
        default=True,
        readonly=True,
        help="Control budget on non-recurring contract confirmation",
    )

    def _create_budget_move_periods(self):
        periods = super()._create_budget_move_periods()
        if self.contract:
            Period = self.env["mis.report.instance.period"]
            model = self.env.ref(
                "budget_control_contract.model_contract_budget_move"
            )
            contract = Period.create(
                {
                    "name": "Contract",
                    "report_instance_id": self.report_instance_id.id,
                    "sequence": 60,
                    "source": "actuals_alt",
                    "source_aml_model_id": model.id,
                    "mode": "fix",
                    "manual_date_from": self.bm_date_from,
                    "manual_date_to": self.bm_date_to,
                }
            )
            periods.update({contract: "-"})
        return periods

    def _budget_info_query(self):
        query = super()._budget_info_query()
        query["info_cols"]["amount_contract"] = ("6_ct_commit", True)
        return query

    def _compute_budget_info(self, **kwargs):
        """ Add more data info budget_info, based on installed modules """
        super()._compute_budget_info(**kwargs)
        self._set_budget_info_amount(
            "amount_contract",
            [("source_aml_model_id.model", "=", "contract.budget.move")],
            kwargs,
            is_commit=True,
        )
