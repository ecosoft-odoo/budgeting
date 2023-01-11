# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Access all OUs' Budget Control",
    "version": "14.0.1.0.0",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "category": "Budget Management",
    "license": "AGPL-3",
    "website": "https://github.com/OCA/account-budgeting",
    "depends": ["budget_control_operating_unit"],
    "data": [
        "security/budget_control_security.xml",
        "security/budget_transfer_security.xml",
    ],
    "installable": True,
    "maintainers": ["Saran440"],
}
