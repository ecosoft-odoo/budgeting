# Copyright 2023 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

{
    "name": "Payment Register Diff - Budget Allocation",
    "version": "15.0.1.0.0",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "website": "https://github.com/OCA/account-analytic",
    "category": "Accounting",
    "depends": [
        "account_payment_multi_deduction",
        "budget_allocation",
    ],
    "data": [
        "wizard/account_payment_register_views.xml",
    ],
    "installable": True,
    "development_status": "Alpha",
    "post_init_hook": "post_init_hook",
    "maintainers": ["ps-tubtim"],
}
