# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Fund Constraint Sequence",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "category": "Accounting",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/account-budgeting",
    "depends": ["fund_constraint"],
    "data": [
        "data/fund_constraint_data.xml",
        "views/fund_constraint_view.xml",
    ],
    "installable": True,
    "post_init_hook": "assign_old_sequences",
}
