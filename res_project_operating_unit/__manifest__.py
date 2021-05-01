# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
{
    "name": "Project Operating Unit",
    "version": "14.0.1.0.0",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "license": "LGPL-3",
    "website": "https://github.com/OCA/account-budgeting",
    "category": "Accounting",
    "depends": ["res_project", "operating_unit"],
    "data": [
        # "report/budget_monitor_report_view.xml",
        "security/res_project_security.xml",
        "views/res_project_views.xml",
    ],
    "installable": True,
}
