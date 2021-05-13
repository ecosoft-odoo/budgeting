# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Program Allocation Dimension - Purchase",
    "summary": "Improve res_program_allocation_dimension for Purchase",
    "version": "14.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/account-budgeting",
    "depends": [
        "budget_dimension_purchase",
        "res_program_allocation_dimension",
    ],
    "data": [
        "views/purchase_view.xml",
    ],
    "installable": True,
    "auto_install": True,
}
