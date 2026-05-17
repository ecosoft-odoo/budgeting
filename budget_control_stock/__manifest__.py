# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Budget Control on Stock (Outbound Consumption)",
    "version": "18.0.2.0.0",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/budgeting",
    "summary": "Commit and consume budget on outbound sale stock moves "
    "(DO at reservation, SVL actual at validation, reverse on return).",
    "depends": [
        "budget_control",
        "stock_analytic",
        "stock_account",
        "sale_stock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/stock_budget_move_views.xml",
        "views/stock_picking_views.xml",
    ],
    "installable": True,
    "maintainers": ["Saran440"],
    "development_status": "Alpha",
}
