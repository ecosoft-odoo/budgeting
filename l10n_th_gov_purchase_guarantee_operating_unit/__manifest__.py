# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Purchase Guarantee - Operating Unit",
    "summary": "Add fields operating unit on purchase guarantee",
    "version": "15.0.1.0.0",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/budgeting",
    "depends": [
        "l10n_th_gov_purchase_guarantee",
        "account_operating_unit",
        "purchase_requisition_operating_unit",
        "purchase_operating_unit",
    ],
    "data": ["views/purchase_guarantee_views.xml"],
    "installable": True,
    "maintainers": ["Saran440"],
    "development_status": "Alpha",
}
