# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Budget Allocation Fund",
    "summary": "Allocate budget by source of fund",
    "version": "14.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/account-budgeting",
    "depends": [
        "budget_allocation",
        "budget_source_fund",
    ],
    "data": [
        "views/account_move_view.xml",
        "views/budget_allocation_view.xml",
    ],
    "installable": True,
}
