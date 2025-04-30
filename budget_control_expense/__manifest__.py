# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Budget Control on Expense",
    "version": "18.0.1.1.0",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/budgeting",
    "depends": ["budget_control", "hr_expense"],
    "data": [
        "security/ir.model.access.csv",
        "views/expense_budget_move.xml",
        "views/budget_period_view.xml",
        "views/hr_expense_view.xml",
        "views/budget_control_view.xml",
        "views/budget_commit_forward_view.xml",
    ],
    "installable": True,
    "maintainers": ["kittiu", "ru3ix-bbb", "Saran440"],
    "development_status": "Alpha",
}
