# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Budget Allocation - Purchase Deposit",
    "version": "15.0.1.0.0",
    "category": "Purchase Management",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/budgeting",
    "depends": [
        "purchase_deposit_analytic",
        "budget_allocation_purchase",
    ],
    "data": [
        "wizard/purchase_make_invoice_advance_views.xml",
    ],
    "installable": True,
    "auto_install": True,
    "maintainers": ["Saran440"],
    "development_status": "Alpha",
}
