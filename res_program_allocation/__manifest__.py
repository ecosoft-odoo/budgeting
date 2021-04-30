# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Program Allocation",
    "summary": "Helper create budget plan, allocation and program all in one",
    "version": "14.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/account-budgeting",
    "depends": ["fund_constraint", "budget_plan", "res_program"],
    "data": [
        "security/ir.model.access.csv",
        "views/fund_constraint_view.xml",
        "views/budget_control_view.xml",
        "views/res_program_allocation_view.xml",
        "views/budget_plan_view.xml",
    ],
    "installable": True,
    "maintainers": ["Saran440"],
    "development_status": "Alpha",
}
