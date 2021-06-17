# Copyright 2021 Ecosoft (<http://ecosoft.co.th>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Budget Transfer Sub State",
    "version": "14.0.1.0.0",
    "category": "Accounting",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/account-budgeting",
    "license": "AGPL-3",
    "depends": ["base_substate", "budget_control_transfer"],
    "data": [
        "data/budget_transfer_substate_mail_template_data.xml",
        "data/budget_transfer_substate_data.xml",
        "views/budget_transfer_view.xml",
    ],
    "demo": [
        "demo/budget_transfer_substate_demo.xml",
    ],
    "installable": True,
}
