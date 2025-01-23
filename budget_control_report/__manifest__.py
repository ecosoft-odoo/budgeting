# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Base Budget Control Report",
    "version": "15.0.1.0.0",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "category": "Accounting",
    "summary": "Report Budget Control",
    "depends": [
        "budget_control",
        "report_xlsx_helper",
    ],
    "data": [
        "security/budget_security.xml",
        "security/ir.model.access.csv",
        "data/report_action.xml",
        "wizard/budget_report_view.xml",
        "wizard/budget_consumption_report_view.xml",
    ],
    "installable": True,
    "development_status": "Alpha",
    "maintainers": ["Saran440"],
}
