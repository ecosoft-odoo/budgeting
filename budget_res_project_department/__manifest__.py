# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Budget Control - with Project and Department",
    "summary": "Integrate project and department with budgeting",
    "version": "15.0.1.0.0",
    "license": "AGPL-3",
    "category": "Budgeting",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/budgeting",
    "depends": [
        "budget_control",
        "res_project",
        "analytic_base_department",
        "hr_department_code",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/analytic_account_data.xml",
        "views/analytic_account_views.xml",
        "views/budget_control_view.xml",
        "views/hr_views.xml",
        "views/res_project_views.xml",
        "wizard/generate_analytic_account.xml",
        "report/budget_monitor_report_view.xml",
    ],
    "maintainers": ["Saran440"],
    "development_status": "Alpha",
}
