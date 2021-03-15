# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Budget Control Transfer Tier Validation",
    "summary": "Extends the functionality of Budget Control Transfer to "
    "support a tier validation process.",
    "version": "14.0.1.0.0",
    "category": "Budgeting Management",
    "website": "https://github.com/OCA/account-budgeting",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": ["budget_control_transfer", "base_tier_validation"],
    "data": [
        "views/budget_transfer_view.xml",
    ],
}
