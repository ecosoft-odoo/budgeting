# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Purchase Stock - Budget Allocation",
    "summary": "Copies the fund of the purchase order item to the stock move",
    "version": "15.0.1.0.0",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/account-analytic",
    "depends": ["purchase_stock", "stock_analytic", "budget_allocation_purchase"],
    "data": [
        "views/stock_move_views.xml",
        "views/stock_scrap.xml",
        "views/stock_move_line.xml",
    ],
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "maintainers": ["Saran440"],
}
