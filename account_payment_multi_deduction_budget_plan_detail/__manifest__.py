# Copyright 2023 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

{
    "name": "Payment Register Diff - Budget Plan Detail",
    "version": "18.0.1.0.1",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "website": "https://github.com/ecosoft-odoo/budgeting",
    "category": "Accounting",
    "depends": [
        "account_payment_multi_deduction",
        "budget_plan_detail",
    ],
    "data": [
        "wizard/account_payment_register_views.xml",
    ],
    "installable": True,
    "development_status": "Alpha",
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "maintainers": ["ps-tubtim", "Saran440"],
}
