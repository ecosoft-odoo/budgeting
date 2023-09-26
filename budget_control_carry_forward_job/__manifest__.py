# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Budget Control Carry Forward - Queue Job",
    "version": "14.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/account-budgeting",
    "depends": ["budget_control", "queue_job"],
    "data": [
        "wizards/budget_commit_forward_info_view.xml",
        "wizards/budget_balance_forward_info_view.xml",
        "views/budget_commit_forward_view.xml",
        "views/budget_balance_forward_view.xml",
    ],
    "installable": True,
    "maintainers": ["Saran440"],
    "development_status": "Alpha",
}
