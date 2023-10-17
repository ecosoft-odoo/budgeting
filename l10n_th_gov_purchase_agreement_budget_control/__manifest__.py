# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Budget Control on Purchase extension on Agreement/No Agreement",
    "version": "15.0.1.0.0",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/budgeting",
    "depends": [
        "budget_control_purchase",
        "l10n_th_gov_purchase_agreement",
    ],
    "data": [
        "views/purchase_view.xml",
        "views/budget_control_view.xml",
        "views/budget_period_view.xml",
    ],
    "installable": True,
    "auto_install": True,
    "maintainers": ["Saran440"],
    "development_status": "Alpha",
}
