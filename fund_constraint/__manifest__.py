# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Fund Constraint",
    "version": "14.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/account-budgeting",
    "depends": ["budget_source_fund"],
    "data": [
        "security/ir.model.access.csv",
        "views/analytic_account_view.xml",
        "views/budget_control_view.xml",
        "views/fund_constraint_view.xml",
        "views/budget_source_fund_view.xml",
        "views/account_move_views.xml",
        "report/source_fund_monitor_report_view.xml",
    ],
    "installable": True,
    "maintainers": ["Saran440"],
    "development_status": "Alpha",
}
