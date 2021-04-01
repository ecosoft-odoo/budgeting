# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class BudgetPeriod(models.Model):
    _inherit = "budget.period"

    advance = fields.Boolean(
        string="On Advance",
        default=False,
        help="Control budget on advance approved",
    )

    def _create_budget_move_periods(self):
        periods = super()._create_budget_move_periods()
        if self.advance:
            Period = self.env["mis.report.instance.period"]
            advance_model = self.env.ref(
                "budget_control_advance_clearing.model_advance_budget_move"
            )
            advance = Period.create(
                {
                    "name": "Advance",
                    "report_instance_id": self.report_instance_id.id,
                    "sequence": 50,
                    "source": "actuals_alt",
                    "source_aml_model_id": advance_model.id,
                    "mode": "fix",
                    "manual_date_from": self.bm_date_from,
                    "manual_date_to": self.bm_date_to,
                }
            )
            periods.update({advance: "-"})
        return periods

    def _set_budget_info_amount(self, source, domain, kwargs):
        budget_info = super()._set_budget_info_amount(source, domain, kwargs)
        if budget_info.get("amount_advance"):
            budget_info["amount_commit"] += budget_info["amount_advance"]
            budget_info["amount_consumed"] = (
                budget_info["amount_commit"] + budget_info["amount_actual"]
            )
        return budget_info

    def _compute_budget_info(self, **kwargs):
        """ Add more data info budget_info, based on installed modules """
        super()._compute_budget_info(**kwargs)
        self._set_budget_info_amount(
            "amount_advance",
            [("source_aml_model_id.model", "=", "advance.budget.move")],
            kwargs,
        )

    @api.model
    def check_budget(self, doclines, doc_type="account"):
        if not doclines:
            return
        if doclines._name == "hr.expense":
            sheet = doclines.mapped("sheet_id")
            sheet.ensure_one()
            if sheet.advance:
                doc_type = "advance"
                self = self.with_context(
                    alt_budget_move_model="advance.budget.move",
                    alt_budget_move_field="advance_budget_move_ids",
                )
        return super().check_budget(doclines, doc_type=doc_type)
