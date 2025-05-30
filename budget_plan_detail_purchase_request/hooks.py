# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command


def _get_installed_dimension_fields(env):
    env.cr.execute("""
        SELECT model, name
        FROM ir_model_fields
        WHERE relation = 'account.analytic.tag'
          AND name LIKE 'x_dimension_%'
    """)
    return {(model, name) for model, name in env.cr.fetchall()}


def post_init_hook(env):
    """Update analytic tag dimension for new module"""
    AnalyticDimension = env["account.analytic.dimension"]
    dimensions = AnalyticDimension.search([])
    # skip it if not dimension
    if not dimensions:
        return

    existing_fields = _get_installed_dimension_fields(env)

    # Model need to update
    model_list = ["purchase.request.line"]

    model_to_update = env["ir.model"].search(
        ["|", ("model", "like", "%.budget.move"), ("model", "in", model_list)],
        order="id",
    )

    for model in model_to_update:
        for dimension in dimensions:
            field_name = AnalyticDimension.get_field_name(dimension.code)
            if (model.model, field_name) in existing_fields:
                continue
            model.write(
                {
                    "field_id": [
                        Command.create(
                            {
                                "name": field_name,
                                "field_description": dimension.name,
                                "ttype": "many2one",
                                "relation": "account.analytic.tag",
                            }
                        )
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
            "DELETE FROM ir_model_fields WHERE name=%s and "
            "model IN ('purchase.request.budget.move', 'purchase.request.line')",
            (name_column,),
        )
