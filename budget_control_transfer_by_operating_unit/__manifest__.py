# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Budget Transfer By Operating Unit",
    "version": "14.0.1.0.0",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "website": "https://github.com/OCA/account-budgeting",
    "category": "Accounting",
    "depends": [
        "budget_control_transfer",
        "budget_control_transfer_operating_unit",
        "budget_control_operating_unit",
    ],
    "data": [
        "views/budget_transfer_view.xml",
    ],
    "installable": True,
}
