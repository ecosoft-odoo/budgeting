# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Budget Control on Expense ref Purchase Request",
    "version": "15.0.1.0.0",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/account-analytic",
    "depends": [
        "budget_control_expense",
        "budget_control_purchase_request",
        "l10n_th_gov_hr_expense",
    ],
    "data": ["views/purchase_request_view.xml"],
    "installable": True,
    "maintainers": ["Saran440"],
    "development_status": "Alpha",
}
