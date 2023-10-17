# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Budget Allocation - Purchase Guarantee Activity",
    "summary": "Add fields activity on purchase guarantee",
    "version": "15.0.1.0.0",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/budgeting",
    "depends": [
        "l10n_th_gov_purchase_guarantee",
        "budget_activity_purchase",
        "budget_activity_purchase_requisition",
    ],
    "data": ["views/purchase_guarantee_method_views.xml"],
    "installable": True,
    "maintainers": ["Saran440"],
    "development_status": "Alpha",
}
