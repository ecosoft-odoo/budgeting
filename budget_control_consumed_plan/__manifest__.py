# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Budget Control - Update Consumed Plan",
    "version": "14.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "summary": "Update consumed amount in plan",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/account-budgeting",
    "depends": ["budget_activity"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "views/budget_control_view.xml",
        "wizards/update_consumed_plan_view.xml",
    ],
    "installable": True,
    "maintainers": ["Saran440"],
    "development_status": "Alpha",
}
