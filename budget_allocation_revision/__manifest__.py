# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Budget Allocation - Revision",
    "version": "15.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "summary": "Keep track of revised by budget allocation",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/budgeting",
    "depends": [
        "budget_allocation",
        "budget_plan_revision",
    ],
    "data": [
        "views/budget_allocation_view.xml",
        "views/budget_plan_view.xml",
        "report/budget_source_fund_report_view.xml",
    ],
    "installable": True,
    "maintainers": ["Saran440"],
    "development_status": "Alpha",
    "post_init_hook": "post_init_hook",
}
