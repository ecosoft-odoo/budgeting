# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Budget Control - Tier Validation",
    "summary": "Extends the functionality of Budget Control to "
    "support a tier validation process.",
    "version": "15.0.1.0.0",
    "category": "Accounting",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/account-analytic",
    "license": "AGPL-3",
    "depends": ["budget_control", "base_tier_validation"],
    "data": [
        "security/budget_control_rules.xml",
        "views/budget_control_view.xml",
    ],
    "application": False,
    "installable": True,
    "maintainers": ["kittiu"],
    "development_status": "Alpha",
}
