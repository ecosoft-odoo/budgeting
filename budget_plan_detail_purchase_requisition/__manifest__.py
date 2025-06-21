# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Budget Plan Detail - Purchase Requisition",
    "version": "18.0.1.0.1",
    "category": "Accounting",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/budgeting",
    "depends": [
        "budget_plan_detail_purchase_request",
        "purchase_request_to_requisition",
    ],
    "data": [
        "views/purchase_requisition_view.xml",
    ],
    "installable": True,
    "auto_install": True,
    "maintainers": ["newtratip", "Saran440"],
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "development_status": "Alpha",
}
