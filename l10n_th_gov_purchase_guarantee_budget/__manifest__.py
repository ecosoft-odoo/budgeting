# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Purchase Guarantee - Budget",
    "summary": "Add fields analytic account, tags and fund on purchase guarantee",
    "version": "15.0.1.0.0",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/account-analytic",
    "depends": [
        "l10n_th_gov_purchase_guarantee",
        "budget_allocation_purchase_requisition",
        "budget_allocation_purchase",
    ],
    "data": ["views/purchase_guarantee_views.xml"],
    "installable": True,
    "maintainers": ["Saran440"],
    "development_status": "Alpha",
    "post_init_hook": "post_init_hook",
}
