# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Budget Allocation Fund for Purchase",
    "summary": "Allocate budget by source of fund for purchase",
    "version": "14.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/account-budgeting",
    "depends": [
        "budget_allocation_fund",
        "purchase",
    ],
    "data": [
        "views/purchase_view.xml",
    ],
    "installable": True,
    "auto_install": True,
}
