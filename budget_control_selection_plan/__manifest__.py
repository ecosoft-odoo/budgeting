# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Budget Control Selection Plan",
    "version": "14.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/account-budgeting",
    "depends": ["budget_control"],
    "data": [
        "security/ir.model.access.csv",
        "views/budget_control_view.xml",
        "views/mis_report_kpi.xml",
        "wizard/generate_budget_control_view.xml",
        "wizard/generate_kpi_view.xml",
    ],
    "installable": True,
    "maintainers": ["Saran"],
    "development_status": "Alpha",
}
