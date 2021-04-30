# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Project Management",
    "summary": "New menu Projects management with analytic",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "category": "Project",
    "website": "https://github.com/OCA/account-budgeting",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "depends": ["base", "mail"],
    "data": [
        "security/res_project_security_groups.xml",
        "security/ir.model.access.csv",
        "data/res_project_cron.xml",
        "views/res_project_menuitem.xml",
        "views/res_project_views.xml",
        "views/res_project_split.xml",
    ],
    "maintainers": ["Saran440"],
    "development_status": "Alpha",
}
