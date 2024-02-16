# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Budget Allocation - Contract Invoice Plan",
    "summary": "Allocate budget for contract invoice plan",
    "version": "15.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/budgeting",
    "depends": [
        "budget_allocation_contract",
        "contract_invoice_plan",
    ],
    "data": ["views/contract_view.xml"],
    "installable": True,
    "auto_install": True,
    "maintainers": ["Saran440"],
}