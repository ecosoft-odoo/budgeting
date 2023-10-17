# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Budget Activity - Purchase Deposit",
    "version": "15.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/budgeting",
    "depends": [
        "purchase_deposit",
        "budget_activity_purchase",
    ],
    "data": [
        "data/purchase_deposit_data.xml",
        "wizard/purchase_make_invoice_advance_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "auto_install": True,
    "maintainers": ["Saran440"],
}
