# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Budget Control on Purchase with Stock",
    "version": "18.0.2.0.0",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/budgeting",
    "depends": ["budget_control_purchase", "budget_control_stock"],
    "data": [
        "views/res_config_settings_views.xml",
        "views/product_category_views.xml",
        "views/purchase_view.xml",
        "views/purchase_budget_move_view.xml",
    ],
    "installable": True,
    "maintainers": ["Saran440"],
    "development_status": "Alpha",
}
