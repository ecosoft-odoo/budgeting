# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Asset Transfer - Allocation (Fund, Tags)",
    "summary": "Add fund and dimension to asset transfer",
    "version": "15.0.1.0.0",
    "license": "AGPL-3",
    "depends": ["account_asset_transfer", "account_asset_fund"],
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/budgeting",
    "category": "Accounting & Finance",
    "data": ["wizard/account_asset_transfer.xml"],
    "installable": True,
    "auto_install": True,
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "maintainers": ["Saran440"],
}
