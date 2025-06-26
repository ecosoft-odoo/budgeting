# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Budget Control - Asset Management",
    "version": "18.0.1.0.0",
    "summary": "Config not affect budget in asset",
    "license": "AGPL-3",
    "depends": ["budget_control", "account_asset_management"],
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/budgeting",
    "category": "Accounting & Finance",
    "data": [
        "views/res_config_settings_views.xml",
        "views/account_asset.xml",
    ],
    "maintainers": ["Saran440"],
    "development_status": "Alpha",
}
