# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Program",
    "summary": "New menu Program master data",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "category": "Accounting",
    "website": "https://github.com/OCA/account-budgeting",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "depends": ["budget_source_fund"],
    "data": [
        "security/ir.model.access.csv",
        "data/program_data.xml",
        "views/res_program_views.xml",
    ],
    "maintainers": ["Saran440"],
    "development_status": "Alpha",
}
