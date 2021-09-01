# Copyright 2021 Ecosoft (<http://ecosoft.co.th>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Budget Control Sub State",
    "version": "14.0.1.0.0",
    "category": "Accounting",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/account-budgeting",
    "license": "AGPL-3",
    "depends": ["base_substate", "budget_control"],
    "data": [
        "data/budget_control_substate_mail_template_data.xml",
        "data/budget_control_substate_data.xml",
        "data/budget_commit_forward_substate_mail_template_data.xml",
        "data/budget_commit_forward_substate_data.xml",
        "views/budget_control_view.xml",
        "views/budget_commit_forward_view.xml",
    ],
    "demo": [
        "demo/budget_control_substate_demo.xml",
        "demo/budget_commit_forward_substate_demo.xml",
    ],
    "installable": True,
}
