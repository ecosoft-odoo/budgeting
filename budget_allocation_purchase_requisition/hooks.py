# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def post_init_hook(cr, registry):
    """Update analytic tag dimension for new module"""
    env = api.Environment(cr, SUPERUSER_ID, {})
    AnalyticDimension = env["account.analytic.dimension"]
    dimensions = AnalyticDimension.search([])
    # skip it if not dimension
    if not dimensions:
        return
    _models = env["ir.model"].search([("model", "=", "purchase.requisition.line")])
    _models.write(
        {
            "field_id": [
                (
                    0,
                    0,
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
