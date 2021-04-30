# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Excel for Program Allocation",
    "summary": "Import/Export Excel for Program Allocation",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/account-budgeting",
    "category": "Accounting",
    "depends": ["excel_import_export", "res_program_allocation"],
    "external_dependencies": {"python": ["pandas", "numpy", "openpyxl"]},
    "data": [
        "views/actions.xml",
        "templates/templates.xml",
    ],
    "installable": True,
}
