# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Budget Control on Purchase",
    "version": "18.0.1.1.0",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/budgeting",
    "depends": ["budget_control", "purchase"],
    "data": [
        "security/ir.model.access.csv",
        "views/budget_period_view.xml",
        "views/budget_control_view.xml",
        "views/budget_commit_forward_view.xml",
        "views/purchase_budget_move.xml",
        "views/purchase_view.xml",
    ],
    "installable": True,
    "maintainers": ["kittiu", "Saran440"],
    "development_status": "Alpha",
}
