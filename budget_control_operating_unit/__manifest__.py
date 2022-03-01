# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
{
    "name": "Budget Control Operating Unit",
    "version": "14.0.1.0.0",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "license": "LGPL-3",
    "website": "https://github.com/OCA/account-budgeting",
    "category": "Accounting",
    "depends": ["budget_control", "analytic_operating_unit"],
    "data": [
        "report/budget_monitor_report_view.xml",
        "security/budget_control_security.xml",
        "views/budget_control_view.xml",
        "views/budget_transfer_view.xml",
        "views/budget_transfer_item_view.xml",
        "views/budget_move_adjustment_view.xml",
    ],
    "installable": True,
}
