# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
{
    "name": "Budget Transfer Operating Unit",
    "version": "14.0.1.0.0",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "license": "LGPL-3",
    "website": "https://github.com/OCA/account-budgeting",
    "category": "Accounting",
    "depends": ["budget_control_transfer", "operating_unit"],
    "data": [
        "security/budget_transfer_security.xml",
        "views/budget_transfer_view.xml",
    ],
    "installable": True,
}
