# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Budget Transfer Dimension",
    "summary": "Budget transfer with dimension",
    "version": "14.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/account-budgeting",
    "depends": ["budget_allocation_dimension", "budget_control_transfer"],
    "data": [
        "views/budget_transfer_item_view.xml",
    ],
    "installable": True,
}
