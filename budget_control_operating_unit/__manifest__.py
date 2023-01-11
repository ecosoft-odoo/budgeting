# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Budget Control - Operating Unit",
    "version": "15.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/account-analytic",
    "depends": ["budget_control", "analytic_operating_unit"],
    "data": [
        "security/budget_control_security.xml",
        "views/res_config_settings_views.xml",
        "views/budget_control_view.xml",
        "views/budget_transfer_view.xml",
        "views/budget_transfer_item_view.xml",
        "views/budget_move_adjustment_view.xml",
        "report/budget_monitor_report_view.xml",
    ],
    "installable": True,
    "post_init_hook": "post_init_hook",
    "maintainers": ["Saran440"],
}
