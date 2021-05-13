# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Program Allocation Dimension",
    "summary": "Allocation budget by dimension",
    "version": "14.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/account-budgeting",
    "depends": [
        "budget_dimension",
        "res_program_allocation",
    ],
    "data": [
        "views/fund_constraint_view.xml",
        "views/res_program_allocation_view.xml",
    ],
    "installable": True,
}
