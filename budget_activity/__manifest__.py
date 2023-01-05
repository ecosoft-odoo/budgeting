# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Budget Activity",
    "version": "15.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/account-budgeting",
    "depends": ["budget_control"],
    "data": [
        "security/budget_activity_security.xml",
        "security/ir.model.access.csv",
        "report/budget_monitor_report_view.xml",
        "views/account_move_views.xml",
        "views/budget_activity_view.xml",
        "views/budget_kpi_view.xml",
        "views/budget_template_view.xml",
        "views/budget_menuitem.xml",
        "views/budget_move_adjustment_view.xml",
    ],
    "installable": True,
    "maintainers": ["kittiu"],
    "development_status": "Alpha",
}
