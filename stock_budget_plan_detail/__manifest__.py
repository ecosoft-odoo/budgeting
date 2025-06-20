# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Stock - Budget Plan Detail",
    "summary": "Add fund, analytic tags dimension in stock move",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/budgeting",
    "depends": ["stock_analytic", "budget_plan_detail", "account_analytic_tag"],
    "data": [
        "views/stock_picking_views.xml",
        "views/stock_move_views.xml",
        "views/stock_move_line.xml",
        "views/stock_scrap.xml",
    ],
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "maintainers": ["Saran440"],
    "development_status": "Alpha",
}
