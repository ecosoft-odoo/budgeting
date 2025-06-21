# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Budget Control - Operating Unit",
    "version": "18.0.1.0.1",
    "category": "Accounting",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/budgeting",
    "depends": ["budget_control", "analytic_operating_unit", "account_operating_unit"],
    "data": [
        "security/budget_control_security.xml",
        "views/budget_control_view.xml",
        "views/budget_transfer_view.xml",
        "views/budget_transfer_item_view.xml",
        "views/budget_move_adjustment_view.xml",
        "report/budget_monitor_report_view.xml",
    ],
    "installable": True,
    "post_init_hook": "post_init_hook",
    "maintainers": ["Saran440"],
    "development_status": "Alpha",
}
