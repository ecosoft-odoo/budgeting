# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Budget Allocation",
    "summary": "Helper create budget plan",
    "version": "14.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/account-budgeting",
    "depends": ["base_automation", "budget_plan"],
    "data": [
        "data/base_automation.xml",
        "security/ir.model.access.csv",
        "views/budget_allocation_view.xml",
        "views/budget_plan_view.xml",
    ],
    "installable": True,
    "maintainers": ["ps-tubtim"],
    "development_status": "Alpha",
}
