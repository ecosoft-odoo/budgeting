# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Res Project - Sequence",
    "version": "15.0.1.0.0",
    "license": "AGPL-3",
    "category": "Project",
    "website": "https://github.com/ecosoft-odoo/budgeting",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "depends": ["res_project"],
    "data": [
        "data/res_project_data.xml",
        "views/res_project_view.xml",
    ],
    "installable": True,
    "post_init_hook": "assign_new_sequences",
}
