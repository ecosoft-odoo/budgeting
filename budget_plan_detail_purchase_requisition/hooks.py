# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command


def post_init_hook(env):
    """Update analytic tag dimension for new module"""
    AnalyticDimension = env["account.analytic.dimension"]
    dimensions = AnalyticDimension.search([])
    # skip it if not dimension
    if not dimensions:
        return
    _models = env["ir.model"].search([("model", "=", "purchase.requisition.line")])
    _models.write(
        {
            "field_id": [
                Command.create(
                    {
                        "name": AnalyticDimension.get_field_name(dimension.code),
                        "field_description": dimension.name,
                        "ttype": "many2one",
                        "relation": "account.analytic.tag",
                    },
                )
                for dimension in dimensions
            ],
        }
    )


def uninstall_hook(env):
    """Cleanup all dimensions before uninstalling."""
    AnalyticDimension = env["account.analytic.dimension"]
    dimensions = AnalyticDimension.search([])
    # drop relation column x_dimension_<code>
    for dimension in dimensions:
        name_column = AnalyticDimension.get_field_name(dimension.code)
        env.cr.execute(
            """DELETE FROM ir_model_fields
            WHERE name=%s and model='purchase.requisition.line'""",
            (name_column,),
        )
