# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Budget Control on Stock",
    "version": "18.0.1.0.1",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/budgeting",
    "depends": ["budget_control", "stock_account", "stock_analytic"],
    "data": [
        "security/ir.model.access.csv",
        "views/stock_budget_move_view.xml",
        "views/stock_picking_type_views.xml",
        "views/stock_picking_view.xml",
        "views/budget_period_view.xml",
        "views/budget_control_view.xml",
        # "views/budget_commit_forward_view.xml",
    ],
    "installable": True,
    "maintainers": ["Saran440"],
    "development_status": "Alpha",
}
