# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Budget Plan - Details",
    "summary": "Allocated budget details",
    "version": "18.0.1.1.2",
    "category": "Accounting",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/budgeting",
    "depends": ["budget_control", "analytic_tag_dimension_enhanced"],
    "data": [
        "security/ir.model.access.csv",
        "data/server_action.xml",
        "data/budget_constraint_data.xml",
        "views/analytic_account_views.xml",
        "views/budget_source_fund_view.xml",
        "views/budget_plan_view.xml",
        "views/budget_plan_line_detail_view.xml",
        "views/budget_control_view.xml",
        "views/budget_transfer_item_view.xml",
        "views/budget_move_adjustment_view.xml",
        "views/account_budget_move.xml",
        "views/account_move_view.xml",
        "report/budget_monitor_report_view.xml",
        "report/budget_source_fund_report_view.xml",
    ],
    "installable": True,
    "maintainers": ["ps-tubtim", "Saran440"],
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "development_status": "Alpha",
}
