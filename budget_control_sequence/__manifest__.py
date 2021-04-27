# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Budget Control Sequence",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "category": "Accounting",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/account-budgeting",
    "depends": ["budget_control"],
    "data": [
        "data/budget_control_data.xml",
        "views/budget_control_view.xml",
    ],
    "installable": True,
    "post_init_hook": "assign_old_sequences",
}
