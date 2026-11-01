# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Budget Plan",
    "summary": "Allocate the budget of a period to analytic accounts",
    "version": "20.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/budgeting",
    "depends": ["budget_control"],
    "data": [
        "security/ir.access.csv",
        "data/analytic_plan_data.xml",
        "wizards/budget_plan_analytic_select_view.xml",
        "views/budget_plan_view.xml",
        "views/budget_control_view.xml",
        "views/budget_period_view.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "maintainers": ["kittiu", "ru3ix-bbb", "Saran440"],
    "development_status": "Alpha",
}
