# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Budget Plan Tier Validation",
    "summary": "Extends the functionality of Budget Plan to "
    "support a tier validation process.",
    "version": "14.0.1.0.0",
    "category": "Accounting",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/account-budgeting",
    "license": "AGPL-3",
    "depends": ["budget_plan", "base_tier_validation"],
    "data": ["views/budget_plan_view.xml"],
    "application": False,
    "installable": True,
    "maintainers": ["ps-tubtim"],
    "development_status": "Alpha",
}
