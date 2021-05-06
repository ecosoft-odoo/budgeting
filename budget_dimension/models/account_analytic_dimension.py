# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.exceptions import UserError


class AccountAnalyticDimension(models.Model):
    _inherit = "account.analytic.dimension"

    @api.model
    def get_model_names(self):
        res = super().get_model_names()
        return res + self.get_budget_move_models()

    @api.model
    def get_budget_move_models(self):
        return ["account.budget.move"]

    @api.model
    def get_budget_report_models(self):
        return ["budget.monitor.report"]

    def get_m2o_field_name(self, code=False):
        return "x_m2o_{}".format(code or self.code).lower()

    @api.model
    def create(self, values):
        res = super().create(values)
        # For dimension with ref_model_id, create another many2one field
        if res.ref_model_id:
            model_list = (
                self.get_budget_move_models() + self.get_budget_report_models()
            )
            _models = self.env["ir.model"].search(
                [("model", "in", model_list)]
            )
            m2o_field_name = self.get_m2o_field_name(values["code"])
            field_name = self.get_field_name(values["code"])
            for _model in _models:
                new_field = self.env["ir.model.fields"].create(
                    {
                        "model_id": _model.id,
                        "name": m2o_field_name,
                        "field_description": values.get("name"),
                        "ttype": "many2one",
                        "relation": res.ref_model_id.model,
                        "readonly": True,
                        "store": True,
                        "index": True,
                    }
                )
                if _model.model in self.get_budget_move_models():
                    new_field.write(
                        {
                            "depends": self.get_field_name(values["code"]),
                            "compute": "for record in self:\n"
                            "  record['{}'] = record.{}.resource_ref and "
                            "record.{}.resource_ref.id".format(
                                m2o_field_name, field_name, field_name
                            ),
                        }
                    )
        return res

    def write(self, vals):
        # Because of compute field which depends on one another,
        # changing code break dependency, system not allowed.
        if "code" in vals:
            raise UserError(
                _(
                    "Changing code is not allowed, please delete and then recreate."
                )
            )
        return super().write(vals)

    def unlink(self):
        """Clean created fields before unlinking."""
        model_list = (
            self.get_budget_move_models() + self.get_budget_report_models()
        )
        _models = self.env["ir.model"].search([("model", "in", model_list)])
        for record in self:
            self.env["ir.model.fields"].search(
                [
                    ("model_id", "in", _models.ids),
                    ("name", "=", self.get_m2o_field_name(record.code)),
                ]
            ).unlink()
        return super().unlink()
