# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Base Tier Validation - Check Budget",
    "summary": "Add option to check budget when a tier is validated",
    "version": "18.0.1.0.0",
    "category": "Tools",
    "website": "https://github.com/ecosoft-odoo/budgeting",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": ["base_tier_validation", "budget_control"],
    "data": [
        "views/tier_definition_view.xml",
    ],
    "maintainers": ["Saran440"],
    "development_status": "Alpha",
}
