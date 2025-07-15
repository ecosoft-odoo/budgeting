# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Project Management",
    "summary": "New menu Projects management",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "category": "Project",
    "website": "https://github.com/ecosoft-odoo/budgeting",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "depends": ["hr", "mail"],
    "data": [
        "security/res_project_security_groups.xml",
        "security/ir.model.access.csv",
        "data/res_project_cron.xml",
        "data/res_project_data.xml",
        "views/res_project_menuitem.xml",
        "views/res_project_views.xml",
        "views/res_project_split.xml",
        "views/hr_department_views.xml",
        "views/hr_employee_views.xml",
        "wizard/split_project_wizard_view.xml",
    ],
    "maintainers": ["Saran440"],
    "development_status": "Alpha",
}
