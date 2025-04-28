# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Budget Activity - Purchase Request",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/budgeting",
    "depends": [
        "budget_activity_purchase",
        "budget_control_purchase_request",
    ],
    "data": [
        "views/purchase_request_view.xml",
        "views/purchase_request_line_view.xml",
        "views/purchase_views.xml",
        "views/purchase_request_budget_move.xml",
    ],
    "installable": True,
    "auto_install": True,
    "maintainers": ["kittiu"],
    "development_status": "Alpha",
}
