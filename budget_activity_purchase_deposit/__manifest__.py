# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Budget Activity - Purchase Deposit",
    "version": "14.0.1.0.0",
    "category": "Purchase Management",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/account-budgeting",
    "depends": [
        "purchase_deposit",
        "budget_purchase_deposit",
    ],
    "data": [
        "data/purchase_deposit_activity_data.xml",
        "data/purchase_deposit_product.xml",
        "wizard/purchase_make_invoice_advance_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "maintainers": ["Saran440"],
}
