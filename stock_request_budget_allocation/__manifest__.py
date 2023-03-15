# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Stock Request - Allocation (Fund, Tags)",
    "summary": "Add fund and dimension to stock request",
    "version": "15.0.1.0.0",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/account-analytic",
    "category": "Warehouse Management",
    "depends": ["stock_request_analytic", "stock_budget_allocation"],
    "data": [
        "views/stock_request_views.xml",
        "views/stock_request_order_views.xml",
    ],
    "installable": True,
    "post_init_hook": "post_init_hook",
    "maintainers": ["Saran440"],
}
