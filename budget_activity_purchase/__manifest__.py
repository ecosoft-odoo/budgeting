# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Budget Activity - Purchase",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/budgeting",
    "depends": [
        "budget_activity",
        "budget_control_purchase",
    ],
    "data": [
        "views/purchase_view.xml",
        "views/purchase_budget_move.xml",
    ],
    "installable": True,
    "auto_install": True,
    "maintainers": ["kittiu", "Saran440"],
    "development_status": "Alpha",
}
