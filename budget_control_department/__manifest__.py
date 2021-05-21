# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Budget Control - Department",
    "summary": "Add fields department on budget control",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "category": "NxPO",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/account-budgeting",
    "depends": [
        "budget_control",
        "res_project_analytic",
        "analytic_base_department",
        "hr_department_code",
    ],
    "data": [
        "data/analytic_group_data.xml",
        "views/analytic_account_views.xml",
        "views/budget_control_view.xml",
        "report/budget_monitor_report_view.xml",
    ],
    "maintainers": ["Saran440"],
    "development_status": "Alpha",
}
