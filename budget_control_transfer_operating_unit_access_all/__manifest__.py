# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Access all OUs' - Budget Transfer",
    "version": "14.0.1.0.0",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "category": "Budget Management",
    "license": "AGPL-3",
    "website": "https://github.com/OCA/account-budgeting",
    "depends": [
        "budget_control_transfer_operating_unit",
        "budget_control_operating_unit_access_all",
    ],
    "data": [
        "security/budget_transfer_security.xml",
    ],
    "installable": True,
    "auto_install": True,
    "maintainers": ["Saran440"],
}
