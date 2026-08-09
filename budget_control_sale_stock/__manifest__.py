# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Budget Control on Sale with Stock",
    "version": "18.0.1.3.0",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/budgeting",
    "depends": [
        "budget_control_stock",
        "sale_stock",
        "sale_project",
        "sale_margin",
        "sale_stock_analytic",
    ],
    "data": [
        "views/res_config_settings_views.xml",
        "views/project_project_views.xml",
        "views/budget_control_views.xml",
        "views/sale_order_views.xml",
    ],
    "installable": True,
    "maintainers": ["Saran440"],
    "development_status": "Alpha",
}
