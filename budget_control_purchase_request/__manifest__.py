# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Budget Control on Purchase Request",
    "version": "18.0.1.1.0",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/budgeting",
    "depends": [
        "budget_control_purchase",
        "purchase_request",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/budget_period_view.xml",
        "views/budget_control_view.xml",
        "views/budget_commit_forward_view.xml",
        "views/purchase_request_line_view.xml",
        "views/purchase_request_view.xml",
        "views/purchase_request_budget_move.xml",
    ],
    "installable": True,
    "maintainers": ["kittiu", "Saran440"],
    "development_status": "Alpha",
}
