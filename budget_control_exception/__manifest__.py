# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Budget Control - Exception",
    "summary": "Custom exceptions on budget control",
    "version": "15.0.1.0.0",
    "category": "Generic Modules/Budget Control",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/budgeting",
    "depends": ["budget_control", "base_exception"],
    "license": "AGPL-3",
    "data": [
        "security/ir.model.access.csv",
        "data/budget_control_exception_data.xml",
        "wizard/budget_control_exception_confirm_view.xml",
        "views/budget_control_exception_view.xml",
    ],
    "installable": True,
    "maintainers": ["Saran440"],
    "development_status": "Alpha",
}
