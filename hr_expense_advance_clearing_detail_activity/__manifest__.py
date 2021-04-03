# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Employee Advance/Clearing - Details Activity",
    "version": "14.0.1.0.0",
    "category": "Human Resources",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "website": "https://github.com/OCA/account-budgeting",  # TODO: hr-expense
    "depends": [
        "hr_expense_advance_clearing_detail",
        "budget_activity_advance_clearing",
    ],
    "data": ["views/hr_expense_views.xml"],
    "installable": True,
    "auto_install": True,
    "maintainers": ["Saran440"],
}
